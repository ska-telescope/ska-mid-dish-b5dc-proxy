"""Specialization of B5dc Device functionality."""

# pylint: disable=abstract-method,too-many-instance-attributes

import asyncio
import dataclasses
import json
import logging
from asyncio import AbstractEventLoop, BaseProtocol, DatagramTransport
from threading import Event, Lock, Thread
from typing import Any, Callable, Optional, Tuple

from ska_control_model import CommunicationStatus, TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device import (
    B5dcDeviceAttenuationException,
    B5dcDeviceConfigureAttenuation,
    B5dcDeviceConfigureFrequency,
    B5dcDeviceFrequencyException,
    B5dcDeviceSensors,
)
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency, B5dcPllState
from ska_mid_dish_dcp_lib.device.b5dc_pca import (
    B5dcFpgaFirmware,
    B5dcIicDevice,
    B5dcPhysicalConfiguration,
)
from ska_mid_dish_dcp_lib.interface.b5dc_interface import B5dcInterface, B5dcPropertyParser
from ska_mid_dish_dcp_lib.protocol.b5dc_protocol import B5dcProtocol, B5dcProtocolTimeout
from ska_tango_base.executor import TaskExecutorComponentManager

from ska_mid_dish_b5dc_proxy.models.constants import B5DC_BUILD_STATE_DEVICE_NAME
from ska_mid_dish_b5dc_proxy.models.data_classes import B5dcBuildStateDataclass

WAIT_BEFORE_CONNECTION_RETRY_SEC = 5
MAX_RETRY_COUNT = 3


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

        self.loop: Optional[AbstractEventLoop] = None
        self._transport: Optional[DatagramTransport] = None
        self._protocol: Optional[BaseProtocol] = None
        self._b5dc_iic: B5dcIicDevice = None
        self._b5dc_pca: B5dcPhysicalConfiguration = None
        self._b5dc_fw: B5dcFpgaFirmware = None

        self._b5dc_property_parser: B5dcPropertyParser = None
        self._b5dc_interface: B5dcInterface = None
        self._b5dc_device_sensors: B5dcDeviceSensors = None
        self._b5dc_device_attn_conf: B5dcDeviceConfigureAttenuation = None
        self._b5dc_device_freq_conf: B5dcDeviceConfigureFrequency = None

        self.loop_thread: Optional[Thread] = None
        # Flag to indicate server connection established
        self._con_established = Event()
        # Lock to prevent contention on request to update B5dc device
        # sensors across the event loops running on different threads
        self._sensor_update_lock = Lock()

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
            buildstate="",
            **kwargs,
        )

    # =============================
    #  Connection handling methods
    # =============================

    def _start_connection_event_loop(self) -> None:
        """Assign server connection task and run event loop."""
        self.loop = asyncio.new_event_loop()
        self.loop.create_task(self._establish_server_connection())
        self.loop.run_forever()

    async def _establish_server_connection(self) -> None:
        """Establish and maintain server connection within event loop."""
        while True:
            if self.loop is None:
                raise RuntimeError("No tasks added on the event loop")
            server_connection_lost = self.loop.create_future()
            self._transport, self._protocol = await self.loop.create_datagram_endpoint(
                lambda: B5dcProtocol(server_connection_lost, self._logger, self._server_addr),
                local_addr=("0.0.0.0", 0),
                remote_addr=self._server_addr,
            )

            # Update B5dc interface objects using newly created
            # transport and protocol
            self._update_b5dc_interface()
            self._b5dc_iic = B5dcIicDevice(self._protocol)
            self._b5dc_fw = B5dcFpgaFirmware(self._logger, self._protocol)
            self._b5dc_pca = B5dcPhysicalConfiguration(self._logger, self._b5dc_iic)
            await self._update_build_state()

            self._con_established.set()

            poll_loop = self.loop.create_task(self._periodically_poll_sensor_values())

            try:
                await server_connection_lost
                self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

                poll_loop.cancel()

                self._con_established.clear()

                self._logger.warning("Reestablishing lost B5dc server connection")
            finally:
                # Clean up transport for later recreation
                if self._transport:
                    self._transport.close()
                await asyncio.sleep(WAIT_BEFORE_CONNECTION_RETRY_SEC)

    def _update_b5dc_interface(self) -> None:
        """Create instances of B5dc freq and atten config and device sensor classes."""
        if self._protocol is None:
            raise RuntimeError("Protocol is not initialized")
        self._b5dc_property_parser = B5dcPropertyParser(self._logger)
        self._b5dc_interface = B5dcInterface(
            self._logger,
            self._b5dc_property_parser,
            get_method=self._protocol.sync_read_register,  # type: ignore
            set_method=self._protocol.sync_write_register,  # type: ignore
        )
        self._b5dc_device_sensors = B5dcDeviceSensors(self._logger, self._b5dc_interface)
        self._b5dc_device_attn_conf = B5dcDeviceConfigureAttenuation(
            self._logger, self._b5dc_interface
        )
        self._b5dc_device_freq_conf = B5dcDeviceConfigureFrequency(
            self._logger, self._b5dc_interface
        )

    def is_connection_established(self) -> bool:
        """Return if connection is established."""
        return self._con_established.is_set()

    # ================================
    #  Sensor synchronisation methods
    # ================================

    async def _update_sensor_with_lock(self, register_name: str) -> None:
        """Acquire the sensor map lock and request b5dc device sensor update."""
        with self._sensor_update_lock:
            await self._b5dc_device_sensors.update_sensor(register_name)

    def sync_register_outside_event_loop(self, register_name: str) -> None:
        """Update singular B5dc device sensor and sync component state."""
        if self.is_connection_established():
            try:
                asyncio.run(self._update_sensor_with_lock(register_name))
                self._update_communication_state(CommunicationStatus.ESTABLISHED)
            except KeyError:
                self._logger.error(
                    f"Error on request to update " f"unknown register: {register_name}"
                )
                return None
            except B5dcProtocolTimeout:
                self._logger.error(
                    f"Protocol exception raised on request to update "
                    f"sensor: {self._reg_to_sensor_map[register_name]}"
                )
                # TODO: In future we want to set the attribute quality to indicate that
                # the value returned is unreliable
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
            self._logger.warning("Connection not yet established or lost")
        return None

    # Polling loop task to be added to event loop in thread
    async def _periodically_poll_sensor_values(self) -> None:
        """Run indefinite loop to periodically update all sensors values."""
        while True:
            if self.is_connection_established():
                await self._update_all_registers()
            await asyncio.sleep(self._polling_period)

    async def _update_all_registers(self) -> None:
        """Update all B5dc device sensors and sync component state."""
        for register, sensor in self._reg_to_sensor_map.items():
            attempt = 0
            while attempt < MAX_RETRY_COUNT:
                try:
                    await self._sync_register_within_event_loop(register)
                    break
                except B5dcProtocolTimeout:
                    attempt += 1
                    self._logger.warning(
                        f"Timeout updating sensor {sensor}. Retry attempt {attempt}"
                    )
                    if attempt >= MAX_RETRY_COUNT:
                        self._logger.warning(
                            f"Exceeded maximum retries for sensor update req: {sensor}"
                        )
                        break
            if attempt >= MAX_RETRY_COUNT:
                break

    async def _sync_register_within_event_loop(self, register_name: str) -> None:
        """Update singular B5dc device sensor and sync component state."""
        if self.is_connection_established():
            try:
                await self._update_sensor_with_lock(register_name)
                self._update_communication_state(CommunicationStatus.ESTABLISHED)
            except KeyError:
                self._logger.error(
                    f"Failure on request to update register " f"value: {register_name}"
                )
            except B5dcProtocolTimeout:
                self._logger.error(
                    f"Protocol exception raised on request to update "
                    f"sensor: {self._reg_to_sensor_map[register_name]}"
                )
                # TODO: In future we want to set the attribute quality to
                # indicate that the value returned is unreliable
                raise

            self._update_component_state(
                **{
                    register_name: getattr(
                        self._b5dc_device_sensors,
                        self._reg_to_sensor_map[register_name],
                    )
                }
            )

    # ==========================
    #  Command handling methods
    # ==========================

    def set_attenuation(
        self,
        attenuation_db: int,
        attn_reg_name: str,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Set the attenuation on the band 5 down converter."""
        status, response = self.submit_task(
            self._set_attenuation,
            args=[attenuation_db, attn_reg_name],
            task_callback=task_callback,
            is_cmd_allowed=self.is_connection_established,
        )
        return status, response

    def _set_attenuation(
        self,
        attenuation_db: int,
        attn_reg_name: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """Set the attenuation on the band 5 down converter."""
        self._logger.debug(
            f"Called SetAttenuation with args (attenuation_db={attenuation_db}, "
            f"attn_reg_name={attn_reg_name})"
        )

        if task_abort_event and task_abort_event.is_set():
            task_callback(  # type: ignore
                status=TaskStatus.ABORTED,
            )
            return

        if task_callback:
            task_callback(
                status=TaskStatus.IN_PROGRESS,
                progress=f"Called SetAttenuation with args "
                f"(attenuation_db={attenuation_db}, attn_reg_name={attn_reg_name})",
            )

        try:
            asyncio.run(self._b5dc_device_attn_conf.set_attenuation(attenuation_db, attn_reg_name))
        except B5dcDeviceAttenuationException as ex:
            self._logger.error(
                f"An error occured on setting the B5dc attenuation " f"on {attn_reg_name}: {ex}"
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
                result=f"SetAttenuation({attenuation_db}, {attn_reg_name}) completed",
            )

    def set_frequency(
        self,
        frequency: int,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Set the frequency on the band 5 down converter."""
        try:
            freq_enum = B5dcFrequency(frequency)
        except ValueError as ex:
            self._logger.error(f"Invalid frequency value supplied: {ex}")
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
            is_cmd_allowed=self.is_connection_established,
        )
        return status, response

    def _set_frequency(
        self,
        frequency: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """Set the frequency on the band 5 down converter."""
        self._logger.debug(f"Called SetFrequency with arg (frequency={frequency})")

        if task_abort_event and task_abort_event.is_set():
            task_callback(  # type: ignore
                status=TaskStatus.ABORTED,
            )
            return

        if task_callback:
            task_callback(
                status=TaskStatus.IN_PROGRESS,
                progress=f"Called SetFrequency with arg (frequency={frequency})",
            )

        try:
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
                result=f"SetFrequency({frequency}) completed",
            )

    def _update_component_state(self, **kwargs: Any) -> None:
        """Log and update new component state."""
        self._logger.debug("Updating B5dc component state with [%s]", kwargs)
        super()._update_component_state(**kwargs)

    def start_communicating(self) -> None:
        """Start the communication with the B5DC device."""
        self._logger.debug("Starting communication with B5DC device")
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        # Start the server connection event loop in a separate thread
        self.loop_thread = Thread(
            target=self._start_connection_event_loop, daemon=True, name="Asyncio loop thread"
        )
        self.loop_thread.start()

    async def _update_build_state(self) -> None:
        if self._b5dc_pca is not None and self._b5dc_fw is not None:
            await self._b5dc_pca.update_pca_info()
            await self._b5dc_fw.update_model_filename()
            await self._b5dc_fw.update_firmware_build_timestamp()

            firmware_file = (
                f"{self._b5dc_fw.b5dc_file_model_name}_{self._b5dc_fw.b5dc_build_time}.fpg"
            )

            b5dc_build_state = B5dcBuildStateDataclass(
                device=B5DC_BUILD_STATE_DEVICE_NAME,
                device_ip=self._server_addr[0],
                device_version=self._b5dc_pca.b5dc_version,
                comms_engine_version=self._b5dc_pca.b5dc_comms_engine_version,
                rfcm_psu_version=self._b5dc_pca.b5dc_rfcm_psu_version,
                rfcm_pcb_version=self._b5dc_pca.b5dc_rfcm_pcb_version,
                backplane_version=self._b5dc_pca.b5dc_backplane_version,
                psu_version=self._b5dc_pca.b5dc_psu_version,
                icd_version=self._b5dc_pca.b5dc_icd_version,
                fpga_firmware_file=firmware_file,
            )
        else:
            b5dc_build_state = B5dcBuildStateDataclass(
                device=B5DC_BUILD_STATE_DEVICE_NAME,
                device_ip="Failed to retrieve build state data for band 5 down converter.",
            )
            self._logger.warning("Build state was not updated successfully.")

        b5dc_build_state_json = json.dumps(dataclasses.asdict(b5dc_build_state), indent=4)
        self._logger.debug("Build state updated: [%s]", b5dc_build_state_json)
        self._update_component_state(buildstate=b5dc_build_state_json)
