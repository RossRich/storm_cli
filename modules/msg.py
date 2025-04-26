import enum
from typing import Dict, Union


class MsgType(str, enum.Enum):
  DATA = "D"
  SETUP = "S"
  CMD = "C"
  DEBUG = "*"
  INV = "INV"


class SerialMsg():
  START_COND = '$'
  END_COND = '!'
  DIV_CHAR = ';'

  def __init__(self, data_len: int = 35):
    self.buffer = 'x' * data_len
    self.start_idx = -1
    self.end_idx = -1
    self.data_list = []
    self.type = MsgType.INV

  def __str__(self):
    return f"***MSG***\ntype: {self.type}\ndata: {self.data_list}\n"

  def reset(self) -> None:
    self.start_idx = -1
    self.end_idx = -1

  def is_data_exist(self) -> bool:
    return self.start_idx != -1 and self.end_idx != -1 and self.end_idx > self.start_idx

  def find_start(self) -> bool:
    self.buffer = SerialMsg.START_COND + self.buffer.split(SerialMsg.START_COND)[-1]
    self.start_idx = self.buffer.find(SerialMsg.START_COND)
    return self.start_idx != -1

  def find_end(self) -> bool:
    if self.start_idx != -1:
      self.end_idx = self.buffer.find(SerialMsg.END_COND, self.start_idx + 1)
      return self.end_idx != -1

    return False

  def parse(self) -> int:
    if not self.is_data_exist():
      return 0

    self.data_list = self.buffer[self.start_idx + 1:self.end_idx].split(SerialMsg.DIV_CHAR)

    try:
      self.type = MsgType(self.data_list[0])
    except Exception as e:
      self.data_list = []
      print(str(e))

    return len(self.data_list)

  def fill(self, data: Dict[str, Union[float, int]], msg_type: MsgType) -> None:
    self.data_list = [msg_type.value]
    self.data_list.extend([str(v) for _, v in data.items()])
    self.type = msg_type

  def serialize(self) -> bytes:
    return (SerialMsg.START_COND + ';'.join(self.data_list) + SerialMsg.END_COND).encode()


class DataMsg():
  H = ("state", "weight", "current", "voltage", "pwm")

  def __init__(self, serial_msg: SerialMsg):
    if serial_msg.type != MsgType.DATA:
      raise RuntimeError("Invalid message type")

    self.msg = serial_msg
    self.d: Dict = {}

  def to_dict(self) -> bool:
    if len(self.msg.data_list) < 5:
      return False

    # индекс 0 для типа сообщения
    for i, h in enumerate(DataMsg.H):
      self.d[h] = self.msg.data_list[i + 1]

    self.d["weight"] = float(self.d["weight"]) / 1000.0
    self.d["current"] = float(self.d["current"]) / 10.0
    self.d["voltage"] = float(self.d["voltage"]) / 10.0

    return True


class SetupMsg():
  H = ("id", "max_throttle", "max_pwm", "min_pwm")

  def __init__(self, serial_msg: SerialMsg):
    if serial_msg.type != MsgType.SETUP:
      raise RuntimeError("Invalid message type")

    self.msg = serial_msg
    self.d: Dict = {}

  def to_dict(self) -> bool:
    if len(self.msg.data_list) < 3:
      return False

    # индекс 0 для типа сообщения
    for i, h in enumerate(SetupMsg.H):
      self.d[h] = self.msg.data_list[i + 1]

    return True
