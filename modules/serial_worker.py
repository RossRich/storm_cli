from abc import ABC, abstractmethod
import time
import serial
from enum import IntEnum, auto
from threading import Event, Thread
from typing import List, Set, Union
from serial.tools.list_ports_common import ListPortInfo
from serial.tools.list_ports import comports as get_serial_devices
from .msg import DataMsg, MsgType, SerialMsg, SetupMsg


class LogLevel(IntEnum):
  INFO = auto()
  ERROR = auto()


class SerialListener(ABC):
  @abstractmethod
  def on_new_measurements(self, data: DataMsg) -> None:
    pass

  @abstractmethod
  def on_new_conf(self, cfg: SetupMsg) -> None:
    pass

  @abstractmethod
  def on_new_device(self, dev: List[ListPortInfo]) -> None:
    pass


class SerialObject(ABC):
  def __init__(self):
    self.listeners: Union[SerialListener, None] = None

  def set_listener(self, listener: SerialListener) -> None:
    self.listeners = listener

  def new_data(self, data: SerialMsg) -> None:
    if self.listeners:
      m = DataMsg(data)
      self.listeners.on_new_measurements(m)

  def new_conf(self, data: SerialMsg) -> None:
    if self.listeners:
      cfg = SetupMsg(data)
      self.listeners.on_new_conf(cfg)

  def new_device(self, dev: List[str]) -> None:
    if self.listeners:
      self.listeners.on_new_device(dev)


class SerialWorker(SerialObject):
  class FMState(IntEnum):
    WAIT = auto()
    SCAN_PORTS = auto()
    CONNECTING = auto()
    READ = auto()
    PARSE = auto()
    WRITE = auto()
    WRITE_SETUP = auto()
    WAIT_RESPONSE = auto()
    PORT_CLEANING = auto()
    CLOSE = auto()

  def __init__(self, rate: int, baudrate: int = 115200) -> None:
    self._label = f"[{self.__class__.__name__}] "
    self._is_stop = Event()
    self._is_stop.clear()
    self._worker_rate = 1.0 / rate
    self._worker = Thread(name="serial_worker", target=self._worker_callback)
    self._fsm_state = SerialWorker.FMState.WAIT
    self._devices: Set[ListPortInfo] = set()
    self._serial_device: str = ""
    self._serial_connection = serial.Serial(baudrate=baudrate, timeout=1)
    self._skip_data_timer = 0
    self._raw_msg = SerialMsg()

    self._is_write_req = False
    self._write_data = SerialMsg()

    self.verbose = False

  def log(self, msg: str, level=LogLevel.INFO) -> None:
    if self.verbose:
      l = "INFO" if level == LogLevel.INFO else "ERROR"
      print(self._label + msg)

  def in_state(self, state: 'SerialWorker.FMState') -> bool:
    return self._fsm_state == state

  def trs(self, new_state: 'SerialWorker.FMState') -> None:
    self.log(f"fsm: {self._fsm_state.name} -> {new_state.name}")
    self._fsm_state = new_state

  def _worker_callback(self) -> None:
    FS = SerialWorker.FMState

    while not self._is_stop.is_set():
      if self._serial_connection.is_open and self._is_write_req:
        self._raw_msg = SerialMsg()
        self.trs(FS.WRITE)

      if self.in_state(FS.WAIT):
        time.sleep(1.0)

      elif self.in_state(FS.SCAN_PORTS):
        new_scan = get_serial_devices()
        if new_scan and set(new_scan).difference(self._devices):
          self._devices = set(new_scan)
          self.new_device([sd.name for sd in new_scan])

        time.sleep(1.0)

      elif self.in_state(FS.CONNECTING):
        if self._serial_connection.is_open:
          self._serial_connection.close()

        try:
          if self._serial_device == "":
            raise RuntimeError("Device not selected")

          self._serial_connection.port = self._serial_device
          self._serial_connection.open()
          self._skip_data_timer = time.monotonic() + 3
          self.trs(FS.PORT_CLEANING)
        except Exception as e:
          self.log("Error: " + str(e))
          self.trs(FS.SCAN_PORTS)

      elif self.in_state(FS.PORT_CLEANING):
        self._serial_connection.read_all()
        if time.monotonic() > self._skip_data_timer:
          self.trs(FS.READ)

      elif self.in_state(FS.READ):
        try:
          if self._serial_connection.in_waiting > 4:
            self._raw_msg.buffer = self._serial_connection.read_until().decode()
            if self._raw_msg.find_start() and self._raw_msg.find_end() and self._raw_msg.is_data_exist():
              self.trs(FS.PARSE)
        except Exception as e:
          self.log(str(e))

      elif self.in_state(FS.PARSE):
        if self._raw_msg.parse():
          if self._raw_msg.type == MsgType.DATA:
            self.new_data(self._raw_msg)
          elif self._raw_msg.type == MsgType.SETUP:
            self.new_conf(self._raw_msg)

        self.trs(FS.READ)

      elif self.in_state(FS.WRITE):
        if not self.model.cmds:
          self._is_write_req = False
          self.trs(FS.READ)
          continue

        if self.model.cmds:
          cmd = self.model.cmds.pop()

          if cmd == CMDS.UPDATE_SETUP:
            # регистрировать каждый WRITE по метке времени и уникальному коды
            # педавать вместе с сообщением уникальный код и проверять ответ массив ожидаемых ответов, как только
            # есть ответ вызвать специальную функцию оповещения
            try:
              msg2 = SerialMsg(60)
              msg2.fill(self.model.hw_setup, MsgType.SETUP)
              self._serial_connection.write(msg2.serialize(self.model.hw_setup, MsgType.SETUP))
              # self.trs(FS.WAIT_RESPONSE)
            except Exception as e:
              print(self._label + f"Failed to receive setup. {e}")
          else:
            try:
              msg = SerialMsg(15)
              self._serial_connection.write(msg.serialize({"CMD": cmd.value}, MsgType.CMD))
              print(self._label + str(msg))
              # self.trs(FS.WAIT_RESPONSE)
            except:
              print(self._label + f"Failed to receive command")
              self.model.cmds.append(cmd)

      elif self.in_state(FS.CLOSE):
        try:
          self._serial_connection.close()
          self.log("Connection terminated")
          self.trs(FS.WAIT)
        except:
          self.log("Error: Failed to terminate connection")

      time.sleep(self._worker_rate)

  def begin(self) -> None:
    self._worker.start()

  def scan_ports(self) -> None:
    self.trs(SerialWorker.FMState.SCAN_PORTS)

  def connect(self, dev: str) -> None:
    new_sd = ""
    last_scan = get_serial_devices()
    for lpi in last_scan:
      if lpi.name == dev:
        new_sd = lpi.device
        break

    if new_sd == "":
      self._devices = set()
      self.trs(SerialWorker.FMState.SCAN_PORTS)
      self.log(f"Invalid serial device: '{dev}'")
    else:
      self._serial_device = new_sd
      self.trs(SerialWorker.FMState.CONNECTING)

  def write(self, data) -> None:
    if self._serial_connection.is_open:
      self._is_write_req = True

  def disconnect(self) -> None:
    # NOTE: не гарантирует остановку, так как заданное состояние может быть переписано в рабочем потоке
    self.trs(SerialWorker.FMState.CLOSE)
    self._devices = set()

  def end(self) -> None:
    self._is_stop.set()
    self._serial_connection.close()
    self._worker.join()
