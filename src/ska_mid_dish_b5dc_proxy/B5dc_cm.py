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



    def _update_component_state(self, *args, **kwargs):
        # TODO: For every component update emit a change event <- Done in component_state_callback in ds
        super()._update_component_state(*args, **kwargs)


