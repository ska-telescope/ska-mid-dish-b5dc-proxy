"""Module containing B5DC buildState data classes."""
import dataclasses

# pylint: disable=too-many-instance-attributes


@dataclasses.dataclass
class B5dcBuildStateDataclass:
    """Dataclass to format B5DC build state data."""

    device: str = ""
    device_ip: str = ""
    device_version: str = ""
    comms_engine_version: str = ""
    rfcm_psu_version: str = ""
    rfcm_pcb_version: str = ""
    backplane_version: str = ""
    psu_version: str = ""
    icd_version: str = ""
    fpga_firmware_file: str = ""
