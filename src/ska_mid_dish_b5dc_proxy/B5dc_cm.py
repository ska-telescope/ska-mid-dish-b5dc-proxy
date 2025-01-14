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
        logger: logging.Logger,
        *args: Any, 
        **kwargs: Any,     
    ) -> None:
        self.logger = logger

        # TODO: Make configurable
        self.logger.setLevel(logging.DEBUG)

    def _update_component_state(self, *args, **kwargs):
        # TODO: For every component update emit a change event <- Done in component_state_callback in ds
        super()._update_component_state(*args, **kwargs)


