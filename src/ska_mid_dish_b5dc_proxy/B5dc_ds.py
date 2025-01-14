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
            self._device._connection_state = CommunicationStatus.NOT_ESTABLISHED

            '''
            It would be easier to name the attributes after the registers but naming them after the variables would make them more readable. This will however
            complicate the component state

            First pass -> have the key of the component state as the register name : have the readable variable name as the attribute name
            '''
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
                self._device.set_change_event(attr, True, False) # !!!!! -> The sensor values will need to be polled
                self._device.set_archive_event(attr, True, False)

            (result_code, message) = super().do()
            return (ResultCode(result_code), message)
def main(args: Any = None, **kwargs: Any) -> None:
    """Launch an instance of the B5dc Tango device."""
    return run((B5dc,), args=args, **kwargs)

if __name__ == "__main__":
    main()
