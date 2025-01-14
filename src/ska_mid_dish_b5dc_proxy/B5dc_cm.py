"""Implementation of B5dc component manager / Specialization of B5dc Device functionality.""" # <- Review this 

import asyncio
from functools import wraps
import threading
import time
from ska_mid_dish_dcp_lib.interface.b5dc_interface import B5dcPropertyParser, B5dcInterface
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcAttenuationBusy, B5dcMappingException, B5dcPllState
from ska_mid_dish_dcp_lib.device.b5dc_device import B5dcDevice
from ska_tango_base.executor import TaskExecutorComponentManager
from ska_mid_dish_dcp_lib.protocol.b5dc_protocol import B5dcProtocol, B5dcProtocolTimeout
from typing import Any
import logging


class B5dcDeviceComponentManager(TaskExecutorComponentManager):
    
    def __init__(
        self: "B5dcDeviceComponentManager",
        b5dc_server_ip: str,
        b5dc_server_port: int,
        b5dc_sensor_update_period: int,
        logger: logging.Logger,
        *args: Any, 
        **kwargs: Any,     
    ) -> None:
        self.logger = logger

        # TODO: Make configurable
        self.logger.setLevel(logging.DEBUG)

        self.polling_period = b5dc_sensor_update_period # We need some configurable rate of polling the sensor values
        
        self.server_addr = (b5dc_server_ip, b5dc_server_port)

        self.loop = asyncio.new_event_loop()
        # self.on_con_lost = self.loop.create_future() <- This shouldnt be global because it completes and could prevent reconnections
        
        # Transport and protocol objects to be assigned on creation on datagram endpoint
        self.transport = None
        self.protocol = None
        
        # Start the event loop in a separate thread 
        self.loop_thread = threading.Thread(target=self.start_event_loop, daemon=True) 
        self.loop_thread.start()

        # Establish server connection and keep event loop running in thread
        asyncio.run_coroutine_threadsafe(self._establish_server_connection(), self.loop)

        # Initialize an instance of the B5dc interface and device classes
        self._b5dc_property_parser = B5dcPropertyParser(self.logger)
        self._b5dc_interface = B5dcInterface(
            self.logger,
            self._b5dc_property_parser,
            get_method=self.protocol.sync_read_register,
            set_method=self.protocol.sync_write_register,
        )
        self._b5dc_device = B5dcDevice(
            self.logger,
            self._b5dc_interface
        )

        # Lock will be used to update the shared sensor_map resource across async methods
        self.sensor_map_lock = asyncio.Lock()

        # Initialize the sensor map references
        self._update_cm_sensor_references()

        super().__init__(
            logger,
            *args,
            spi_rfcm_frequency=0,
            spi_rfcm_pll_lock=B5dcPllState.NOT_LOCKED,
            spi_rfcm_h_attenuation=0,
            spi_rfcm_v_attenuation=0,
            spi_rfcm_photo_diode_ain0=0,
            spi_rfcm_rf_in_h_ain1=0,
            spi_rfcm_rf_in_v_ain2=0,
            spi_rfcm_if_out_h_ain3=0,
            spi_rfcm_if_out_v_ain4=0,
            spi_rfcm_rf_temp_ain5=0,
            spi_rfcm_psu_pcb_temp_ain7=0,
            **kwargs,
        )
        # Following init, start up polling loop that periodically updates sensor state values of the device object
        self.b5dc_state_synchronization_thread = threading.Thread(
            target=self._wrap_polling_function,
            daemon=True
        )
        self.b5dc_state_synchronization_thread.start()


    def start_event_loop(self): 
        asyncio.set_event_loop(self.loop) 
        self.loop.run_forever()

    # Method that maintains connection to the server
    async def _establish_server_connection(self) -> None:
        while True:
            self.server_connection_lost = self.loop.create_future()

            self.transport, self.protocol = await self.loop.create_datagram_endpoint(
                lambda: B5dcProtocol(self.server_conection_lost, 
                    self.logger, 
                    self.server_addr),
                local_addr=("0.0.0.0", 0),
                remote_addr=self.server_addr,
            )
            
            self.logger.info("B5DC server connection created")
            try:
                await self.server_connection_lost
                self.logger.warning("Connection to the underlying B5DC server lost. Attempting to reestablish one")
            finally:
                # Clean up transport and protocol and recreate transport
                if self.transport:
                    self.transport.close()
                self.transport = None
                self.protocol = None
                await asyncio.sleep(5)


    # Method to implement the period polling of the sensors to ensure
    def _wrap_polling_function(self):
        asyncio.run(self._poll_sensor_attributes())
    async def _poll_sensor_attributes(self):
        while True:
            # This may need to be wrapped in some sort of check to make sure the 
            await self._sync_all_component_states()
            time.sleep(self.polling_period)

    
    # Simulate connection_lost callback
    def kill_transport(self):
        # self.transport.close()
        self.protocol.connection_lost(None)


    # This method will be used to update the component manager internal references to the Device class sensors
    # Explore if there is a smarter way to do this, ie: update a single reference only
    def _update_cm_sensor_references(self):
        self.sensor_map = {
                "spi_rfcm_frequency" : self._b5dc_device.sensors.rfcm_frequency,
                "spi_rfcm_pll_lock" : self._b5dc_device.sensors.rfcm_pll_lock,
                "spi_rfcm_h_attenuation" : self._b5dc_device.sensors.rfcm_h_attenutation_db,
                "spi_rfcm_v_attenuation" : self._b5dc_device.sensors.rfcm_v_attenutation_db,
                "spi_rfcm_photo_diode_ain0" : self._b5dc_device.sensors.clk_photodiode_current_ma,
                "spi_rfcm_rf_in_h_ain1" : self._b5dc_device.sensors.h_pol_rf_power_in_dbm,
                "spi_rfcm_rf_in_v_ain2" : self._b5dc_device.sensors.v_pol_rf_power_in_dbm,
                "spi_rfcm_if_out_h_ain3" : self._b5dc_device.sensors.h_pol_if_power_out_dbm,
                "spi_rfcm_if_out_v_ain4" : self._b5dc_device.sensors.v_pol_if_power_out_dbm,
                "spi_rfcm_rf_temp_ain5" : self._b5dc_device.sensors.rf_temperature_degc,
                "spi_rfcm_psu_pcb_temp_ain7" : self._b5dc_device.sensors.rfcm_psu_pcb_temperature_degc,
            }
        
    # This method will make sure that the transport exists and is not closing before attempting
    # to publish a request to the b5dc server
    def verify_transport_available(self, func):
        @wraps(func)
        async def inner(self, *args: Any, **kwargs: Any) -> Any:
            if (self.transport is not None) and (not self.transport.is_closing()):
                result = await func(*args, **kwargs)
                return result
            else:
                self.logger.warning("B5DC component manager transport is None, closing or closed")
            return inner
    

    # The function of this method is to ensure that the component state value reflect
    # the value of the underlying sensor value. The component managers references to the device class sensors are 
    # also refreshed
    # @verify_transport_available
    async def _sync_component_state(self, register_name: str) -> None:
        # This check has be done for the "all sync" too, so maybe pop in a decorator?
        if (self.transport is not None) and (not self.transport.is_closing()): 
            try:
                await self._b5dc_device.sensors.update_sensor(register_name) 
            except (B5dcMappingException, B5dcProtocolTimeout, B5dcAttenuationBusy) as ex:
                self.logger.error(f"Failed to sync component state: {ex}")
                return None

            async with self.sensor_map_lock:
                self._update_cm_sensor_references()

            self._update_component_state(**{register_name: self.sensor_map[register_name]})
        else:
            self.logger.error("B5DC component manager transport is None, closing or closed (Single state sync)")






    # The function of the next method is to refresh all sensor values, and consequently their component states
    # If a sensor value changes the value change should be archived and a change event emitted by the device
    # @verify_transport_available
    async def _sync_all_component_states(self) -> None:
        # This check has be done across multiple methods, so maybe pop in a decorator?
        if (self.transport is not None) and (not self.transport.is_closing()): 
            # Persist previous values of the sensor map
            init_sensor_states = self.sensor_map

            # Request B5DC sensor device update all sensor values and update internal references
            try:
                await self._b5dc_device.sensors.update_state()
            except (B5dcMappingException, B5dcProtocolTimeout, B5dcAttenuationBusy) as ex:
                self.logger.error(f"A failure occured while trying to sync all sensor states {ex}")
                return None

            async with self.sensor_map_lock:
                self._update_cm_sensor_references()

            # Compare prior sensor states and update component states if needed
            for register in self.sensor_map:
                if self.sensor_map[register] != init_sensor_states[register]:
                    self._update_component_state(**{register: self.sensor_map[register]})
        else:
            self.logger.error("B5DC component manager transport is None, closing or closed (All states sync)")


    def _update_component_state(self, *args, **kwargs):
        # TODO: For every component update emit a change event <- Done in component_state_callback in ds
        super()._update_component_state(*args, **kwargs)


