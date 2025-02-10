from typing import Dict, List, Union
from .msg import DataMsg, SerialMsg
from .cmds import CMDS
from .observer import ObsEvent, Publisher
from serial.tools.list_ports_common import ListPortInfo

def debug_msg(msg, is_debug_enabled = True):
  if is_debug_enabled:
    print(msg)

class Model(Publisher):
  def __init__(self) -> None:
    super().__init__()
    
    self._label = f"[{self.__class__.__name__}] "
    self.serial_data: Dict[str, Union[int, float]] = {}
    self.is_client_connected = False
    self.is_port_opened = False
    self.ports: List[ListPortInfo] = []
    self.port: ListPortInfo = ListPortInfo("invalid", True)
    self.baudrate = 115200
    self.cmds: List[CMDS] = []
    self.hw_setup: Dict[str, int] = {}

  def connection_port(self, port: ListPortInfo, baudrate: int = 115200) -> None:
    self.port = port
    self.baudrate = baudrate

  def set_ports_list(self, port: Union[List, ListPortInfo]) -> None:
    # TODO: использовать множество "set"

    if isinstance(port, ListPortInfo):
      if port not in self.ports:
        self.ports.append(port)
        self.notify(ObsEvent.NEW_PORT)
    elif isinstance(port, List):
      new_ports = [p for p in port if p not in self.ports]
      if len(new_ports) != 0:
        self.ports.extend(new_ports)
        self.notify(ObsEvent.NEW_PORT)

  def set_uart_data(self, msg: SerialMsg) -> None:
    try:
      data_msg = DataMsg(msg)
    except:
      debug_msg(self._label + "Failed to create dict from MSG")
      return

    if data_msg.to_dict():
      self.serial_data = data_msg.d
      self.notify(ObsEvent.NEW_DATA)
    else:
      debug_msg(self._label + "Failed to create dict from MSG")

  def set_new_cmd(self, cmd: CMDS) -> None:
    debug_msg(self._label + f"New cmd: {cmd}")
    self.cmds.append(cmd)
    self.notify(ObsEvent.NEW_CMD)

  def update_hw_setup(self, data: Dict) -> None:
    debug_msg(self._label + "Update params")
    self.hw_setup = data
    self.notify(ObsEvent.UPDATE_SETUP)