from typing import Any, Dict, List, Union
from .msg import DataMsg, SerialMsg, SetupMsg
from .observer import ObsEvent, Publisher
from serial.tools.list_ports_common import ListPortInfo


def debug_msg(msg, is_debug_enabled=True):
  if is_debug_enabled:
    print(msg)


class Model(Publisher):
  def __init__(self) -> None:
    super().__init__()
    self._label = f"[{self.__class__.__name__}] "
    self.is_client_connected = False
    self.is_port_opened = False
    self.devices: List[str] = []
    self.device: str = ""
    self.baudrate = 115200
    self.serial_data: DataMsg = None
    self.cfg: Dict[str, Any] = {}
    self.setup_id = 1  # 0 - зарезервирован для системы
