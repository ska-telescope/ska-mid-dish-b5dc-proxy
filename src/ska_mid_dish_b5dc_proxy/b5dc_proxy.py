"""Tango device for monitoring B5DC register values and executing device commands."""

# pylint: disable=protected-access,invalid-name

from typing import Any, List, Optional, Tuple

from ska_control_model import CommunicationStatus, ResultCode
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency, B5dcPllState
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import SubmittedSlowCommand
from tango import AttrWriteType, is_omni_thread
from tango.server import attribute, command, device_property, run

from ska_mid_dish_b5dc_proxy.b5dc_cm import B5dcDeviceComponentManager

DevVarLongStringArrayType = Tuple[List[ResultCode], List[Optional[str]]]


class B5dcProxy(SKABaseDevice):
    """Implementation of the B5dcProxy Tango device."""

    # -----------------
    # Device Properties
    # -----------------
    B5dc_endpoint = device_property(dtype=str, default_value="127.0.0.1:10001")
    B5dc_sensor_update_period = device_property(dtype=str, default_value="10")

    class InitCommand(SKABaseDevice.InitCommand):
        """Initializes the attributes of the B5dc Tango device."""

        def do(
            self: SKABaseDevice.InitCommand,
            *args: Any,
            **kwargs: Any,
        ) -> tuple[ResultCode, str]:
            """
            Initialise B5dc tango device.

            :param args: positional arguments
            :param kwargs: keyword arguments

            :return: A tuple containing a return code and a string
            """
            self._device._component_state_attr_map = {
                "buildstate": "buildState",
                "spi_rfcm_frequency": "rfcmFrequency",
                "spi_rfcm_pll_lock": "rfcmPllLock",
                "spi_rfcm_h_attenuation": "rfcmHAttenuation",
                "spi_rfcm_v_attenuation": "rfcmVAttenuation",
                "spi_rfcm_photo_diode_ain0": "clkPhotodiodeCurrent",
                "spi_rfcm_rf_in_h_ain1": "hPolRfPowerIn",
                "spi_rfcm_rf_in_v_ain2": "vPolRfPowerIn",
                "spi_rfcm_if_out_h_ain3": "hPolRfPowerOut",
                "spi_rfcm_if_out_v_ain4": "vPolRfPowerOut",
                "spi_rfcm_rf_temp_ain5": "rfTemperature",
                "spi_rfcm_psu_pcb_temp_ain7": "rfcmPsuPcbTemperature",
            }
            # Configure change and archive events for all attribute in the map
            for attr in self._device._component_state_attr_map.values():
                self._device.set_change_event(attr, True, False)
                self._device.set_archive_event(attr, True, False)

            self._device.set_change_event("connectionState", True, False)
            self._device.set_archive_event("connectionState", True, False)

            (result_code, message) = super().do()  # type: ignore
            self._device.component_manager.start_communicating()
            return ResultCode(result_code), message

    def create_component_manager(self: "B5dcProxy") -> B5dcDeviceComponentManager:
        """
        Create B5dc component manager.

        :return: The B5dc component manager
        """
        B5dc_server_ip = self.B5dc_endpoint.split(":")[0]
        B5dc_server_port = int(self.B5dc_endpoint.split(":")[1])
        return B5dcDeviceComponentManager(
            B5dc_server_ip,
            B5dc_server_port,
            int(self.B5dc_sensor_update_period),
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def init_command_objects(self) -> None:
        """Initialize the command handlers."""
        super().init_command_objects()

        for command_name, method_name in [
            ("SetHPolAttenuation", "set_attenuation"),
            ("SetVPolAttenuation", "set_attenuation"),
            ("SetFrequency", "set_frequency"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    logger=self.logger,
                ),
            )

    def _communication_state_changed(self, communication_state: CommunicationStatus) -> None:
        """Push and archive events on communication state change."""
        self.push_change_event("connectionState", communication_state)
        self.push_archive_event("connectionState", communication_state)

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args: Any, **kwargs: Any) -> None:
        """Push and archive events on component state change."""
        for comp_state_name, comp_state_value in kwargs.items():
            attribute_name = self._component_state_attr_map.get(comp_state_name, comp_state_name)
            setattr(self, attribute_name, comp_state_value)

            # TODO: On attribute read a segfault occurs where is_omni_thread()
            # returns True. Some investigation is required to determine the
            # cause of this issue.
            if not is_omni_thread():
                self.push_change_event(attribute_name, comp_state_value)
                self.push_archive_event(attribute_name, comp_state_value)

    # ===========
    # Attributes
    # ===========
    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Return the status of the connection to the B5dc server endpoint",
    )
    def connectionState(self) -> CommunicationStatus:
        """Return the status of the connection to the B5dc server endpoint."""
        return self.component_manager.communication_state

    @attribute(dtype=str)
    def buildState(self) -> str:
        """Get B5DC version information."""
        return self.component_manager.component_state.get("buildstate")

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Indicates the PLL Output Frequency. The default value is 11.1 GHz",
    )
    def rfcmFrequency(self: "B5dcProxy") -> float:
        """Reflect the PLL output frequency in GHz."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_frequency")
        return self.component_manager.component_state.get("spi_rfcm_frequency", 0.0)

    @attribute(
        dtype=B5dcPllState,
        access=AttrWriteType.READ,
        doc="Status flags for RFCM PLL lock and lock loss detection.",
    )
    def rfcmPllLock(self: "B5dcProxy") -> B5dcPllState:
        """Return the Phase lock loop state."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_pll_lock")
        return self.component_manager.component_state.get(
            "spi_rfcm_pll_lock", B5dcPllState.NOT_LOCKED
        )

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the RFCM H-polarization attenuation value in dB.",
    )
    def rfcmHAttenuation(self: "B5dcProxy") -> float:
        """Return the rfcmHAttenuation."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_h_attenuation")
        return self.component_manager.component_state.get("spi_rfcm_h_attenuation", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the RFCM V-polarization attenuation value in dB.",
    )
    def rfcmVAttenuation(self: "B5dcProxy") -> float:
        """Return the rfcmVAttenuation."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_v_attenuation")
        return self.component_manager.component_state.get("spi_rfcm_v_attenuation", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the photodiode current in mA.",
    )
    def clkPhotodiodeCurrent(self: "B5dcProxy") -> float:
        """Return the photo diode current."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_photo_diode_ain0")
        return self.component_manager.component_state.get("spi_rfcm_photo_diode_ain0", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the RFCM RF power input for horizonal polarization in dBm.",
    )
    def hPolRfPowerIn(self: "B5dcProxy") -> float:
        """Return the hPolRfPowerIn."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_rf_in_h_ain1")
        return self.component_manager.component_state.get("spi_rfcm_rf_in_h_ain1", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the RFCM RF power input for vertical polarization in dBm.",
    )
    def vPolRfPowerIn(self: "B5dcProxy") -> float:
        """Return the vPolRfPowerIn."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_rf_in_v_ain2")
        return self.component_manager.component_state.get("spi_rfcm_rf_in_v_ain2", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the RFCM RF power output for horizonal polarization in dBm.",
    )
    def hPolRfPowerOut(self: "B5dcProxy") -> float:
        """Return the hPolRfPowerOut."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_if_out_h_ain3")
        return self.component_manager.component_state.get("spi_rfcm_if_out_h_ain3", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the RFCM RF power output for vertical polarization in dBm.",
    )
    def vPolRfPowerOut(self: "B5dcProxy") -> float:
        """Return the vPolRfPowerOut sensor value."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_if_out_v_ain4")
        return self.component_manager.component_state.get("spi_rfcm_if_out_v_ain4", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects the RFCM RF PCB temperature in deg C.",
    )
    def rfTemperature(self: "B5dcProxy") -> float:
        """Return the of the RFCM RF PCB in deg."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_rf_temp_ain5")
        return self.component_manager.component_state.get("spi_rfcm_rf_temp_ain5", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reflects RFCM PSU PCB temperature in deg C.",
    )
    def rfcmPsuPcbTemperature(self: "B5dcProxy") -> float:
        """Return the temperature of the RFCM PSU PCB in deg."""
        self.component_manager.sync_register_outside_event_loop("spi_rfcm_psu_pcb_temp_ain7")
        return self.component_manager.component_state.get("spi_rfcm_psu_pcb_temp_ain7", 0.0)

    # =========
    # Commands
    # =========
    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
        doc_in="""Set the horizontal polarization attenuation on the band 5 down converter.

        :param attenuation_db: value to set in dB [0-31dB]
        """,
    )
    def SetHPolAttenuation(self: "B5dcProxy", attenuation_db: int) -> DevVarLongStringArrayType:
        """Set the horizontal polarization attenuation on the band 5 down converter."""
        handler = self.get_command_object("SetHPolAttenuation")
        result_code, unique_id = handler(attenuation_db, "spi_rfcm_h_attenuation")
        return [result_code], [unique_id]

    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
        doc_in="""Set the vertical polarization attenuation on the band 5 down converter.

        :param attenuation_db: value to set in dB [0-31dB]
        """,
    )
    def SetVPolAttenuation(self: "B5dcProxy", attenuation_db: int) -> DevVarLongStringArrayType:
        """Set the vertical polarization attenuation on the band 5 down converter."""
        handler = self.get_command_object("SetVPolAttenuation")
        result_code, unique_id = handler(attenuation_db, "spi_rfcm_v_attenuation")
        return [result_code], [unique_id]

    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
        doc_in="""Set the frequency on the band 5 down converter.

        :param frequency: frequency to set [B5dcFrequency.F_11_1_GHZ(1),
        B5dcFrequency.F_13_2_GHZ(2) or B5dcFrequency.F_13_86_GHZ(3)]
        """,
    )
    def SetFrequency(self: "B5dcProxy", frequency: B5dcFrequency) -> DevVarLongStringArrayType:
        """Set the frequency on the band 5 down converter."""
        handler = self.get_command_object("SetFrequency")
        result_code, unique_id = handler(frequency)
        return [result_code], [unique_id]


def main(args: Any = None, **kwargs: Any) -> None:
    """Launch an instance of the B5dcProxy Tango device."""
    return run((B5dcProxy,), args=args, **kwargs)


if __name__ == "__main__":
    main()
