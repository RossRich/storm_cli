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
    self.data = 'x' * data_len
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
    self.data = SerialMsg.START_COND + self.data.split(SerialMsg.START_COND)[-1]
    self.start_idx = self.data.find(SerialMsg.START_COND)
    return self.start_idx != -1

  def find_end(self) -> bool:
    if self.start_idx != -1:
      self.end_idx = self.data.find(SerialMsg.END_COND, self.start_idx + 1)
      return self.end_idx != -1

    return False

  def parse(self) -> int:
    if not self.is_data_exist():
      return 0

    self.data_list = self.data[self.start_idx + 1:self.end_idx].split(SerialMsg.DIV_CHAR)

    try:
      self.type = MsgType(self.data_list[0])
    except Exception as e:
      self.data_list = []
      print(str(e))

    return len(self.data_list)

  def fill(self, data: Dict[str, Union[float, int]], msg_type: MsgType) -> None:
    self.data_list = [msg_type.value]
    self.data_list.extend([v for _, v in data.items()])
    self.type = msg_type

  def serialize(self, data: Dict[str, Union[float, int]], msg_type: MsgType) -> bytes:
    self.fill(data, msg_type)
    return (SerialMsg.START_COND + ';'.join(self.data_list) + SerialMsg.END_COND).encode()


class DataMsg():
  def __init__(self, serial_msg: SerialMsg):

    if serial_msg.type != MsgType.DATA:
      raise RuntimeError("Invalid message type")

    self.msg = serial_msg
    self.d = {"state": 0, "weight": 0.0, "current": 0.0, "voltage": 0.0, "pwm": 0}

  def to_dict(self) -> bool:
    if len(self.msg.data_list) < 5:
      return False

    # индекс 0 для типа сообщения
    _index = 1
    self.d["state"] = self.msg.data_list[_index]
    _index += 1
    self.d["weight"] = float(self.msg.data_list[_index]) / 1000.0
    _index += 1
    self.d["current"] = float(self.msg.data_list[_index]) / 10.0
    _index += 1
    self.d["voltage"] = float(self.msg.data_list[_index]) / 10.0
    _index += 1
    self.d["pwm"] = self.msg.data_list[_index]
    return True


class SetupMsg():
  def __init__(self, serial_msg: SerialMsg):

    if serial_msg.type != MsgType.SETUP:
      raise RuntimeError("Invalid message type")

    self.msg = serial_msg
    self.d = {"max_throttle": 0, "max_pwm": 0, "min_pwm": 0}

  def to_dict(self) -> bool:
    if len(self.msg.data_list) < 3:
      return False

    # индекс 0 для типа сообщения
    h = ("max_throttle", "max_pwm", "min_pwm")
    for i, h in enumerate(h):
      self.d[h] = self.msg.data_list[i + 1]

    return True
