"""Specialization of B5dc Device functionality."""

# pylint: disable=abstract-method,too-many-instance-attributes

import asyncio
import logging
import threading
from typing import Any, Callable, Optional, Tuple

from ska_control_model import TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device import (
    B5dcDeviceAttenuationException,
    B5dcDeviceConfigureAttenuation,
    B5dcDeviceConfigureFrequency,
    B5dcDeviceFrequencyException,
    B5dcDeviceSensors,
)
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency, B5dcPllState
from ska_mid_dish_dcp_lib.interface.b5dc_interface import B5dcInterface, B5dcPropertyParser
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
        self._logger = logger
        self._logger.setLevel(logging.DEBUG)
        self._polling_period = b5dc_sensor_update_period
        self._server_addr = (b5dc_server_ip, b5dc_server_port)

        self.loop = None
        self._transport = None
        self._protocol = None

        self._reg_to_sensor_map = {
            "spi_rfcm_frequency": "rfcm_frequency",
            "spi_rfcm_pll_lock": "rfcm_pll_lock",
            "spi_rfcm_h_attenuation": "rfcm_h_attenuation_db",
            "spi_rfcm_v_attenuation": "rfcm_v_attenuation_db",
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
            spi_rfcm_frequency=0.0,
            spi_rfcm_pll_lock=B5dcPllState.NOT_LOCKED,
            spi_rfcm_h_attenuation=0.0,
            spi_rfcm_v_attenuation=0.0,
            spi_rfcm_photo_diode_ain0=0.0,
            spi_rfcm_rf_in_h_ain1=0.0,
            spi_rfcm_rf_in_v_ain2=0.0,
            spi_rfcm_if_out_h_ain3=0.0,
            spi_rfcm_if_out_v_ain4=0.0,
            spi_rfcm_rf_temp_ain5=0.0,
            spi_rfcm_psu_pcb_temp_ain7=0.0,
            **kwargs,
        )

        # Start the server connection event loop in a separate thread
        self.loop_thread = threading.Thread(
            target=self._start_connection_event_loop, daemon=True, name="Asyncio loop thread"
        )
        self.loop_thread.start()

        # Flag to indicate server connection established
        self._con_established = threading.Event()

        # Lock to prevent contention on request to update B5dc device sensors
        self._sensor_update_lock = asyncio.Lock()

    def _start_connection_event_loop(self) -> None:
        """Assign server connection task and run event loop."""
        self.loop = asyncio.new_event_loop()
        self.loop.create_task(self._establish_server_connection())
        self.loop.run_forever()

    # pylint: disable=attribute-defined-outside-init
    async def _establish_server_connection(self) -> None:
        """Establish and maintain server connection within event loop."""
        while True:
            server_connection_lost = self.loop.create_future()
            self._transport, self._protocol = await self.loop.create_datagram_endpoint(
                lambda: B5dcProtocol(server_connection_lost, self._logger, self._server_addr),
                local_addr=("0.0.0.0", 0),
                remote_addr=self._server_addr,
            )

            self._b5dc_property_parser = B5dcPropertyParser(self._logger)
            self._b5dc_interface = B5dcInterface(
                self._logger,
                self._b5dc_property_parser,
                get_method=self._protocol.sync_read_register,
                set_method=self._protocol.sync_write_register,
            )
            self._b5dc_device_sensors = B5dcDeviceSensors(self._logger, self._b5dc_interface)

            # TODO: It may be tricky to configure these here because if they dont
            # exist yet and a client attempts to call the command
            # an exception will be thrown
            self._b5dc_device_attn_conf = B5dcDeviceConfigureAttenuation(
                self._logger, self._b5dc_interface
            )
            self._b5dc_device_freq_conf = B5dcDeviceConfigureFrequency(
                self._logger, self._b5dc_interface
            )

            # Sync component state to sensor values on connection start before
            # setting polling loop
            self._con_established.set()

            self.loop.create_task(self._periodically_poll_sensor_values())

            try:
                await server_connection_lost
                self._logger.warning(
                    "Connection to B5DC server lost. \
                    Cleaning up and attempting to re-establish"
                )
            finally:
                # Clean up transport for later recreation
                if self._transport:
                    self._transport.close()
                await asyncio.sleep(5)

    async def _update_sensor_with_lock(self, register_name: str) -> None:
        """Acquire the sensor map lock and request b5dc device sensor update."""
        async with self._sensor_update_lock:
            await self._b5dc_device_sensors.update_sensor(register_name)

    # Update a single sensor value, and the component state from outside the event loop
    def sync_register_outside_event_loop(self, register_name: str) -> None:
        """Update singular B5dc device sensor and sync component state."""
        if self._con_established.is_set():
            try:
                asyncio.run(self._update_sensor_with_lock(register_name))
            except KeyError:
                self._logger.error(f"Error on request to update unknown register: {register_name}")
                return None
            except RuntimeError as ex:
                self._logger.error(
                    f"Error while requesting update to register {register_name}: {ex}"
                )
                return None

            self._update_component_state(
                **{
                    register_name: getattr(
                        self._b5dc_device_sensors,
                        self._reg_to_sensor_map[register_name],
                    )
                }
            )
        else:
            self._logger.warning(
                "Connection not yet established or component state \
                not yet synchronized to b5dc device"
            )
        return None

    # Update a single sensor value, and the component state from inside the event loop
    async def _sync_register_within_event_loop(self, register_name: str) -> None:
        """Update singular B5dc device sensor and sync component state."""
        if self._protocol.connection_established:
            try:
                await self._update_sensor_with_lock(register_name)
            except KeyError:
                self._logger.error(f"Failure on request to update register value: {register_name}")

            self._update_component_state(
                **{
                    register_name: getattr(
                        self._b5dc_device_sensors,
                        self._reg_to_sensor_map[register_name],
                    )
                }
            )
        else:
            self._logger.warning("Connection not yet established")

    # Polling loop task to be added to event loop in thread
    async def _periodically_poll_sensor_values(self) -> None:
        """Run indefinite loop to periodically update all sensors values."""
        while True:
            if self._con_established.is_set():
                await self._update_all_registers()
            await asyncio.sleep(self._polling_period)

    async def _update_all_registers(self) -> None:
        """Update all B5dc device sensors and sync component state."""
        for register in self._reg_to_sensor_map:
            await self._sync_register_within_event_loop(register)

    def _update_component_state(self, **kwargs: Any) -> None:
        """Log and update new component state."""
        self._logger.debug("Updating B5dc component state with [%s]", kwargs)
        super()._update_component_state(**kwargs)

    def is_connection_established(self) -> bool:
        """Return if connection is established."""
        return self._con_established.is_set()

    # TODO: Remove divider > Command handling functions down here ++++++++++
    # pylint: disable=unused-argument
    def set_attenuation(
        self,
        attenuation_db: int,
        attn_reg_name: str,
        task_abort_event: Any,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Set the attenuation on the band 5 down converter."""
        status, response = self.submit_task(
            self._set_attenuation,
            args=[attenuation_db, attn_reg_name],
            task_callback=task_callback,
        )
        return status, response

    # pylint: disable=unused-argument
    def _set_attenuation(
        self,
        attenuation_db: int,
        attn_reg_name: str,
        task_abort_event: Any,
        task_callback: Optional[Callable] = None,
    ) -> None:
        """Set the attenuation on the band 5 down converter."""
        self._logger.info(
            f"Called SetAttenuation with args (attenuation_db={attenuation_db}, "
            f"attn_reg_name={attn_reg_name})"
        )

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            asyncio.run(self._b5dc_device_attn_conf.set_attenuation(attenuation_db, attn_reg_name))
        except B5dcDeviceAttenuationException as ex:
            self._logger.error(
                f"An error occured on setting the B5dc attenuation on {attn_reg_name}: {ex}"
            )
            if task_callback:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=f"An error occured on setting the B5dc attenuation "
                    f"on {attn_reg_name}: {ex}",
                )
            return

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                result="SetAttenuation completed",
            )

    # pylint: disable=unused-argument
    def set_frequency(
        self,
        frequency: B5dcFrequency,
        task_abort_event: Any,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Set the frequency on the band 5 down converter."""
        try:
            freq_enum = B5dcFrequency(frequency)
        except ValueError as ex:
            self._logger.error(
                f"Invalid frequency value supplied. " f"The following exception was raised: {ex}"
            )
            return (
                TaskStatus.REJECTED,
                f"Invalid frequency value supplied: {frequency}. Expected "
                f"B5dcFrequency enum value (ie: B5dcFrequency.F_11_1_GHZ(1), "
                f"B5dcFrequency.F_13_2_GHZ(2) or B5dcFrequency.F_13_86_GHZ(3))",
            )

        status, response = self.submit_task(
            self._set_frequency,
            args=[freq_enum],
            task_callback=task_callback,
        )
        return status, response

    # pylint: disable=unused-argument
    def _set_frequency(
        self,
        frequency: B5dcFrequency,
        task_abort_event: Any,
        task_callback: Optional[Callable] = None,
    ) -> None:
        """Set the frequency on the band 5 down converter."""
        self._logger.info(f"Called SetFrequency with arg (frequency={frequency})")

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            # TODO: Can this async method be run in the already existing event loop?
            asyncio.run(self._b5dc_device_freq_conf.set_frequency(frequency))
        except B5dcDeviceFrequencyException as ex:
            self._logger.error(f"An error occured on setting the B5dc frequency: {ex}")
            if task_callback:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=f"An error occured on setting the B5dc frequency: {ex}",
                )
            return

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                result="SetFrequency completed",
            )
