"""Specialization of B5dc Device functionality."""

# pylint: disable=abstract-method,too-many-instance-attributes

import asyncio
import logging
import threading
import time
from typing import Any

from ska_mid_dish_dcp_lib.device.b5dc_device import B5dcDevice
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcPllState
from ska_mid_dish_dcp_lib.interface.b5dc_interface import (
    B5dcInterface,
    B5dcPropertyParser,
)
from ska_mid_dish_dcp_lib.protocol.b5dc_protocol import B5dcProtocol
from ska_tango_base.executor import TaskExecutorComponentManager


class B5dcDeviceComponentManager(TaskExecutorComponentManager):
    """Component manager enabling monitoring and control of the B5DC device."""

    def __init__(
        self: "B5dcDeviceComponentManager",
        b5dc_server_ip: str,
        b5dc_server_port: int,
        b5dc_sensor_update_period: int,
        logger: logging.Logger,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialize B5dcDeviceComponentManager.

        :param b5dc_server_ip: IP address of the B5DC server.
        :param b5dc_server_port: Port on which to communicate with the B5DC server.
        :param b5dc_sensor_update_period: B5DC device sensor value polling period.
        :param args: positional arguments to pass to the parent class.
        :param kwargs: keyword arguments to pass to the parent class.
        """
        self.logger = logger
        self.logger.setLevel(logging.DEBUG)  # TODO: Make configurable
        self.polling_period = b5dc_sensor_update_period
        self.server_addr = (b5dc_server_ip, b5dc_server_port)

        # Init event loop and run coroutine to establish and maintain datagram endpoint
        self.loop = asyncio.new_event_loop()
        self.transport = None
        self.protocol = None

        # Start the event loop in a separate thread
        self.loop_thread = threading.Thread(
            target=self._start_connection_event_loop, daemon=True
        )
        self.loop_thread.start()

        # Establish server connection and keep event loop running in thread
        self.connection_established = threading.Event()

        # Initialize cm instances of the B5dc interface and device classes,
        # but wait for protocol to be established
        self.connection_established.wait()
        self._b5dc_property_parser = B5dcPropertyParser(self.logger)
        self._b5dc_interface = B5dcInterface(
            self.logger,
            self._b5dc_property_parser,
            get_method=self.protocol.sync_read_register,
            set_method=self.protocol.sync_write_register,
        )
        self._b5dc_device = B5dcDevice(self.logger, self._b5dc_interface)

        self.reg_to_sensor_map = {
            "spi_rfcm_frequency": "rfcm_frequency",
            "spi_rfcm_pll_lock": "rfcm_pll_lock",
            "spi_rfcm_h_attenuation": "rfcm_h_attenutation_db",
            "spi_rfcm_v_attenuation": "rfcm_v_attenutation_db",
            "spi_rfcm_photo_diode_ain0": "clk_photodiode_current_ma",
            "spi_rfcm_rf_in_h_ain1": "h_pol_rf_power_in_dbm",
            "spi_rfcm_rf_in_v_ain2": "v_pol_rf_power_in_dbm",
            "spi_rfcm_if_out_h_ain3": "h_pol_if_power_out_dbm",
            "spi_rfcm_if_out_v_ain4": "v_pol_if_power_out_dbm",
            "spi_rfcm_rf_temp_ain5": "rf_temperature_degc",
            "spi_rfcm_psu_pcb_temp_ain7": "rfcm_psu_pcb_temperature_degc",
        }

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
        asyncio.run(self._sync_all_component_states())
        self.loop.create_task(self._periodically_poll_sensor_values())

    def _start_connection_event_loop(self) -> None:
        """Assign server connection task and run event loop."""
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._establish_server_connection())
        self.loop.run_forever()

    async def _establish_server_connection(self) -> None:
        """Establish and maintain server connection."""
        while True:
            server_connection_lost = self.loop.create_future()
            self.transport, self.protocol = await self.loop.create_datagram_endpoint(
                lambda: B5dcProtocol(
                    server_connection_lost, self.logger, self.server_addr
                ),
                local_addr=("0.0.0.0", 0),
                remote_addr=self.server_addr,
            )
            self.connection_established.set()
            try:
                await server_connection_lost
                self.logger.warning(
                    "Connection to B5DC server lost.\
                    Cleaning up and attempting to re-establish one"
                )
            finally:
                # Clean up transport for later recreation
                if self.transport:
                    self.transport.close()
                await asyncio.sleep(5)

    async def _sync_component_state(self, register_name: str) -> None:
        """Sync component state to respective B5dc device sensor."""
        if self.protocol.connection_established:
            init_sensor_val = getattr(
                self._b5dc_device.sensors, self.reg_to_sensor_map[register_name]
            )
            try:
                await self._b5dc_device.sensors.update_sensor(register_name)
            except KeyError:
                print(f"Failure on request to update register value: {register_name}")
            updated_sensor_val = getattr(
                self._b5dc_device.sensors, self.reg_to_sensor_map[register_name]
            )

            if init_sensor_val != updated_sensor_val:
                self._update_component_state(
                    **{
                        register_name: getattr(
                            self._b5dc_device.sensors,
                            self.reg_to_sensor_map[register_name],
                        )
                    }
                )
        else:
            self.logger.warning(
                "B5DC component manager transport is\
                None, closing or closed (Single state sync)"
            )

    async def _sync_all_component_states(self) -> None:
        """Sync all component states to B5dc device sensors."""
        for register in self.reg_to_sensor_map:
            await self._sync_component_state(register)

    async def _periodically_poll_sensor_values(self) -> None:
        """Run indefinite loop to poll B5dc sensor values."""
        if self.connection_established.is_set():
            while True:
                await self._sync_all_component_states()
                time.sleep(self.polling_period)

    def _update_component_state(self, *args: Any, **kwargs: Any) -> None:
        """Log and update new component state."""
        self.logger.debug("Updating B5dc component state with [%s]", kwargs)
        super()._update_component_state(*args, **kwargs)
