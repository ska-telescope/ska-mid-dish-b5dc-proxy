"""Tango device for monitoring B5DC register values and executing device commands"""

import asyncio

from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import SubmittedSlowCommand
from ska_control_model import ResultCode, CommunicationStatus
from B5dc_cm import B5dcDeviceComponentManager
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency, B5dcPllState

from tango.server import attribute, command, run
from tango import AttrWriteType

from typing import Any, Tuple, List, Optional

DevVarLongStringArrayType = Tuple[List[ResultCode], List[Optional[str]]]

class B5dc(SKABaseDevice):
    """Implementation of the B5dc Tango device."""

    # -----------------
    # Device Properties
    # -----------------
    B5dc_server_ip = "127.0.0.1"
    B5dc_server_port = 10001
    B5dc_sensor_update_period = 100

    class InitCommand(SKABaseDevice.InitCommand):
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

            # REVIEW: Sensor names used for attrs rather than reg names?
            self._device._component_state_attr_map = {
                "spi_rfcm_frequency" : "rfcmFrequency",
                "spi_rfcm_pll_lock" : "rfcmPllLock",
                "spi_rfcm_h_attenuation" : "rfcmHAttenutation",
                "spi_rfcm_v_attenuation" : "rfcmVAttenutation",
                "spi_rfcm_photo_diode_ain0" : "clkPhotodiodeCurrent",
                "spi_rfcm_rf_in_h_ain1" : "hPolRfPowerIn",
                "spi_rfcm_rf_in_v_ain2" : "vPolRfPowerIn",
                "spi_rfcm_if_out_h_ain3" : "hPolRfPowerOut",
                "spi_rfcm_if_out_v_ain4" : "vPolRfPowerOut",
                "spi_rfcm_rf_temp_ain5" : "rfTemperature",
                "spi_rfcm_psu_pcb_temp_ain7" : "rfcmPsuPcbTemperature",
            }
            # Configure change and archive events for all attribute in the map
            for attr in self._device._component_state_attr_map.values():
                self._device.set_change_event(attr, True, False)
                self._device.set_archive_event(attr, True, False)

            (result_code, message) = super().do()
            return (ResultCode(result_code), message)
        
    def create_component_manager(self: "B5dc") -> B5dcDeviceComponentManager:
        """
        Create B5dc component manager.

        :return: The B5dc component manager
        """
        return B5dcDeviceComponentManager(
            self.B5dc_server_ip,
            self.B5dc_server_port,
            self.B5dc_sensor_update_period,
            logger=self.logger,
            component_state_callback=self._component_state_changed,
        )
    
    def init_command_objects(self):
        """Initialize the command handlers."""
        super().init_command_objects()

        for command_name, method_name in [
            ("SetAttenuation", "set_attenuation"),
            ("SetFrequency", "set_frequency"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    callback=None,
                    logger=self.logger,
                )
            )

    def _component_state_changed(self, *args: Any, **kwargs: Any):
        """Callback triggered on change in component state to enable pushing of change and archive events."""
        if not hasattr(self, "_component_state_attr_map"):
            self.logger.warning("Init not completed, but state is being updated [%s]", kwargs)
            return

        for comp_state_name, comp_state_value in kwargs.items():
            attribute_name = self._component_state_attr_map.get(comp_state_name, comp_state_name)
            setattr(self, attribute_name, comp_state_value)
            self.push_change_event(attribute_name, comp_state_value)
            self.push_archive_event(attribute_name, comp_state_value)
    
    # -----------
    # Attributes
    # -----------
    '''
        -> All sensor values are read only from the perspective of the client
        On Sensor read:
            -> (In component manager) -> Using B5dc_device_sensors_object call -> update_sensor("Register name")
                                            -> We must update the sensor value everytime because we are not guaranteed the most uptodate 
                                            component state from polling
                                      -> The component state is now updated with the latest sensor value
                                      -> Return the component state value as the value of the attribute
    '''
    # TODO: REMOVE THIS <- easy way to trigger connection_lost event on protocol object
    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
    )
    def killTransport(self: "B5dc") -> float:
        # TODO: Update the corresponding component state value
        self.component_manager.kill_transport()
        return 1.0


    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def rfcmFrequency(self: "B5dc") -> float:
        asyncio.run(self.component_manager._sync_component_state("spi_rfcm_frequency"))
        return self.component_manager.component_state.get("spi_rfcm_frequency")
    
    @attribute(
        dtype=B5dcPllState,
        doc="",
        access=AttrWriteType.READ,
    )
    def rfcmPllLock(self: "B5dc") -> float:
        asyncio.run(self.component_manager._sync_component_state("spi_rfcm_pll_lock"))
        return self.component_manager.component_state.get("spi_rfcm_pll_lock")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def rfcmHAttenutation(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_h_attenuation")
        return self.component_manager.component_state.get("spi_rfcm_h_attenuation")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def rfcmVAttenutation(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_v_attenuation")
        return self.component_manager.component_state.get("spi_rfcm_v_attenuation")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def clkPhotodiodeCurrent(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_photo_diode_ain0")
        return self.component_manager.component_state.get("spi_rfcm_photo_diode_ain0")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def hPolRfPowerIn(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_rf_in_h_ain1")
        return self.component_manager.component_state.get("spi_rfcm_rf_in_h_ain1")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def vPolRfPowerIn(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_rf_in_v_ain2") 
        return self.component_manager.component_state.get("spi_rfcm_rf_in_v_ain2")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def hPolRfPowerOut(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_if_out_h_ain3") 
        return self.component_manager.component_state.get("spi_rfcm_if_out_h_ain3")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def vPolRfPowerOut(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_if_out_v_ain4") 
        return self.component_manager.component_state.get("spi_rfcm_if_out_v_ain4")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def rfTemperature(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_rf_temp_ain5") 
        return self.component_manager.component_state.get("spi_rfcm_rf_temp_ain5")
    
    @attribute(
        dtype=float,
        doc="",
        access=AttrWriteType.READ,
    )
    def rfcmPsuPcbTemperature(self: "B5dc") -> float:
        self.component_manager._sync_component_state("spi_rfcm_psu_pcb_temp_ain7")
        return self.component_manager.component_state.get("spi_rfcm_psu_pcb_temp_ain7")

    # -----------
    # Commands 
    # -----------
    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
    )
    def SetAttenuation(self: "B5dc", attenuation_db: int) -> DevVarLongStringArrayType:
        """Set the attenuation on the band 5 down converter.

        :param set_attenutation_db: value to set in dB
        """
        handler = self.get_command_object("SetAttenuation")
        result_code, unique_id = handler(attenuation_db)
        return([result_code], [unique_id])
    
    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
    )

    def SetFrequency(self: "B5dc", frequency: B5dcFrequency) -> DevVarLongStringArrayType:
        """Set the frequency on the band 5 down converter.

        :param frequency: frequency to set
        """
        handler = self.get_command_object("SetFrequency")
        result_code, unique_id = handler(frequency)
        return([result_code], [unique_id])
    

def main(args: Any = None, **kwargs: Any) -> None:
    """Launch an instance of the B5dc Tango device."""
    return run((B5dc,), args=args, **kwargs)

if __name__ == "__main__":
    main()
