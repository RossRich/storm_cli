from typing import Any, Dict, List, Union
from .msg import DataMsg


class Model():
  def __init__(self) -> None:
    super().__init__()
    self._label = f"[{self.__class__.__name__}] "
    self.is_client_connecmax_throttleted = False
    self.is_port_opened = False
    self.devices: List[str] = []
    self.device: str = ""
    self.baudrate = 115200
    self.measurements: Dict[str, Any] = {}
    self.cfg: Dict[str, Any] = {}
    self.setup_id = 1  # 0 - зарезервирован для системы
