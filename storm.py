#!/bin/python3

from abc import ABC, abstractmethod
from ctypes import Structure, c_bool, c_float, c_int
from json import load
import queue
from typing import Any, Callable, Dict, List, Union
from enum import Enum, IntEnum, auto, unique
from threading import Event, Thread
import time
import serial
from flask import Flask, abort, redirect, url_for
from flask import render_template
from flask_socketio import Namespace, SocketIO, emit
import serial.tools
import serial.tools.list_ports
from serial.tools.list_ports_common import ListPortInfo
from static_data import Templates
import pathlib

DATA_STORAGE = "data"

DEBUG_ENABLED = True
UPDATE_UI_DATA_DT = 0.25 # задержка обновления данных в интрерфейсе, сек


class CMDS(Enum):
  START_TEST = "101"
  START_CALIB = "212"
  STOP_TEST = "254"


def debug_msg(msg):
  global DEBUG_ENABLED
  if DEBUG_ENABLED:
    print(msg)


class SerialMsg():
  DATA_LEN = 27
  START_COND = '$'
  END_COND = '!'

  def __init__(self):
    self.data = 'x' * SerialMsg.DATA_LEN
    self.start_idx = -1
    self.end_idx = -1
    self.len = 0
    self.data_list = []
    self.d = {"state": 0, "weight": 0.0, "current": 0.0, "voltage": 0.0, "pwm": 0}

  def __str__(self):
    return self.data

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
    self.data_list = self.data[self.start_idx + 1:self.end_idx].split(';')
    return len(self.data_list)

  def to_dict(self) -> None:
    if len(self.data_list) >= 5:
      self.d["state"] = self.data_list[0]
      self.d["weight"] = float(self.data_list[1]) / 1000.0
      self.d["current"] = float(self.data_list[2]) / 10.0
      self.d["voltage"] = float(self.data_list[3]) / 10.0
      self.d["pwm"] = self.data_list[4]


@unique
class ObsEvent(IntEnum):
  CONNECTION = auto()
  DISCONNECTION = auto()
  NEW_DATA = auto()
  NEW_PORT = auto()
  SELECT_PORT = auto()
  NEW_CMD = auto()


class Subscriber():
  def __init__(self) -> None:
    pass

  def update(self, event: ObsEvent) -> None:
    pass


class Publisher():
  def __init__(self) -> None:
    self._subs: List[Subscriber] = []

  def add_subs(self, subscriber: Subscriber) -> None:
    self._subs.append(subscriber)

  def notify(self, event: ObsEvent) -> None:
    for s in self._subs:
      s.update(event)


class Model(Publisher):
  def __init__(self) -> None:
    super().__init__()
    self._label = f"[{self.__class__.__name__}] "
    self.serial_data: Dict[str, float] = {}
    self.is_client_connected = False
    self.is_port_opened = False
    self.ports: List[ListPortInfo] = []
    self.port: ListPortInfo = ListPortInfo("invalid", True)
    self.baudrate = 115200
    self.cmds: List[CMDS] = []

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

  def set_uart_data(self, data) -> None:
    self.serial_data = data
    self.notify(ObsEvent.NEW_DATA)

  def set_new_cmd(self, cmd: CMDS) -> None:
    debug_msg(self._label + f"New cmd: {cmd}")
    self.cmds.append(cmd)


class SerialWorker():
  class FMStates(IntEnum):
    WAIT = auto()
    SCAN_PORTS = auto()
    CONNECTING = auto()
    READ = auto()
    PARSE = auto()
    WRITE_CMD = auto()
    CLOSE = auto()

  def __init__(self, rate: int, model: Model) -> None:
    self._label = f"[{self.__class__.__name__}] "
    self._is_stop = Event()
    self._is_stop.clear()
    self._rate = 1.0 / rate
    self.worker = Thread(name="serial_worker",
                         target=self._worker_callback)
    self._timer = time.monotonic()
    self._state = SerialWorker.FMStates.WAIT
    self.serial_port = serial.Serial()
    self.model = model
    self.msg = SerialMsg()
    self.ports = []
    self._is_write_req = False
    self._is_file_open = False
    self._data_storage = pathlib.Path(DATA_STORAGE)
    self._skip_data_timer = 0

  @property
  def fsm_state(self) -> 'SerialWorker.FMStates':
    return self._state

  def in_state(self, state: 'SerialWorker.FMStates') -> bool:
    return self.fsm_state == state

  def trs(self, new_state: 'SerialWorker.FMStates') -> None:
    debug_msg(self._label + f"Transition: {self._state.name} -> {new_state.name}")
    self._state = new_state

  def _worker_callback(self) -> None:
    FS = SerialWorker.FMStates

    while not self._is_stop.is_set():
      if self.in_state(FS.WAIT):
        time.sleep(1.0)
      elif self.in_state(FS.SCAN_PORTS):
        self.ports = serial.tools.list_ports.comports()
        debug_msg(self._label + f"{[p.name for p in self.model.ports]}")
        if len(self.ports) > 0:
          self.model.set_ports_list(self.ports)
        time.sleep(1.0)
      elif self.in_state(FS.CONNECTING):
        if self.model.port.name == "invalid" or self.model.baudrate <= 0:
          debug_msg("Bad port")
          self.trs(FS.WAIT)
          continue

        self.serial_port.port = self.model.port.device
        self.serial_port.baudrate = self.model.baudrate

        try:
          self.serial_port.open()
          self._skip_data_timer = time.monotonic() + 5
          self.trs(FS.READ)
        except Exception as e:
          debug_msg("Error: " + str(e))
          self.trs(FS.SCAN_PORTS)

      elif self.in_state(FS.READ):
        try:
          if self.serial_port.in_waiting > 5 and self._skip_data_timer < time.monotonic():
            self.msg.data = self.serial_port.read_until().decode()
            # print(self.msg)
            if self.msg.find_start() and self.msg.find_end() and self.msg.is_data_exist():
              self.trs(FS.PARSE)
        except Exception as e:
          print(str(e))

      elif self.in_state(FS.PARSE):
        self.msg.parse()
        self.msg.to_dict()
        # print(self.msg.d)
        # if (self.msg.d["state"] == 4 and not self._is_file_open):
          # file_name = 
        self.model.set_uart_data(self.msg.d)
        self.trs(FS.READ)

      elif self.in_state(FS.WRITE_CMD):
        if len(self.model.cmds) == 0:
          self._is_write_req = False
          self.trs(FS.READ)
          continue

        self.serial_port.write(str.encode(self.model.cmds.pop().value))

      elif self.in_state(FS.CLOSE):
        try:
          self.serial_port.close()
          self.trs(FS.WAIT)
          print("Port close")
        except:
          pass

      if self._is_write_req:
        self.trs(FS.WRITE_CMD)
        continue

      time.sleep(self._rate)

  def begin(self) -> None:
    self.worker.start()

  def scan_ports(self) -> None:
    self.trs(SerialWorker.FMStates.SCAN_PORTS)

  def connect(self) -> None:
    self.trs(SerialWorker.FMStates.CONNECTING)

  def start_test(self) -> None:
    if self.serial_port.is_open:
      self._is_write_req = True

  def disconnect(self) -> None:
    self.trs(SerialWorker.FMStates.CLOSE)

  def end(self) -> None:
    self._is_stop.set()
    self.serial_port.close()
    self.worker.join()


class SocketWorker(Namespace):
  def __init__(self, model: Model, namespace: Union[str, None] = None) -> None:
    super().__init__(namespace)
    self.model = model
    self._label = f"[{self.__class__.__name__}] "

  def on_connect(self):
    debug_msg(self._label + "on_connect")
    self.model.is_client_connected = True
    self.model.notify(ObsEvent.CONNECTION)

  def on_disconnect(self):
    debug_msg(self._label + "on_disconnect")
    self.model.is_client_connected = False
    self.model.notify(ObsEvent.DISCONNECTION)

  def on_select_port(self, data):
    debug_msg(self._label + str(data))
    port_name = data["name"]

    for i in self.model.ports:
      if port_name == i.name:
        self.model.port = i
        self.model.notify(ObsEvent.SELECT_PORT)
        break

  def on_new_cmd(self, data):
    debug_msg(self._label + "New test request")
    cmd = CMDS(data["cmd"])
    self.model.set_new_cmd(cmd)
    self.model.notify(ObsEvent.NEW_CMD)

  def update_serial_data(self) -> bool:
    self.emit("update_serial_data", self.model.serial_data)

  def update_ports_list(self) -> bool:
    if not self.model.is_client_connected:
      debug_msg(self._label + "Client not connected")
      return False

    if len(self.model.ports) == 0:
      debug_msg(self._label + "No serail ports")
      return False

    obj = [{"index": i, "value": p.name} for i, p in enumerate(self.model.ports)]
    debug_msg(self._label + str(obj))
    self.emit("new_port", obj)
    debug_msg(self._label + "Update ports")

  def request(self, data):
    pass
    # self.model.serial_data = data
    # print("uart data:", data)


class Controller(Subscriber):
  def __init__(self, flask_app: Flask, socket: SocketWorker, serial_worker: SerialWorker, model: Model) -> None:
    self._label = f"[{self.__class__.__name__}] "
    self.socket = socket
    self.model = model
    self.serial = serial_worker
    self._update_data_timer = 0

    self.event_handlers: Dict[ObsEvent, Callable[[ObsEvent], None]] = {
      ObsEvent.CONNECTION: self.on_connection,
      ObsEvent.DISCONNECTION: self.on_disconnection,
      ObsEvent.NEW_DATA: self.update_data,
      ObsEvent.NEW_PORT: self.update_ports,
      ObsEvent.SELECT_PORT: self.connect_to_port,
      ObsEvent.NEW_CMD: self.send_cmd
    }

  def on_connection(self, ignore) -> None:
    debug_msg(self._label + "New connection")
    self.serial.scan_ports()

  def on_disconnection(self, ignore) -> None:
    debug_msg(self._label + "Disconnection")
    self.serial.disconnect()
    self.model.ports.clear()

  def update_data(self, i) -> None:
    if self._update_data_timer < time.monotonic():
      self._update_data_timer = time.monotonic() + UPDATE_UI_DATA_DT
      self.socket.update_serial_data()

  def update_ports(self, i) -> None:
    self.socket.update_ports_list()

  def connect_to_port(self, i) -> None:
    if self.model.port.name != "invalid":
      self.serial.connect()

  def send_cmd(self, event: ObsEvent) -> None:
    debug_msg(self._label + "Start cmd")
    self.serial.start_test()

  def update(self, event: ObsEvent) -> None:
    handler = self.event_handlers.get(event, None)
    if handler:
      handler(event)


app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)


@app.errorhandler(500)
def no_serial(error) -> str:
  return render_template(Templates.no_serial), 500


@app.route("/")
def home() -> str:
  return render_template(Templates.index)


if __name__ == "__main__":

  if not pathlib.Path(DATA_STORAGE).exists():
    debug_msg(f"[SYS] Create folder {DATA_STORAGE}")
    pathlib.Path(DATA_STORAGE).mkdir(parents=True, exist_ok=True)

  model = Model()
  sw = SerialWorker(30, model)
  socket_ns = SocketWorker(model, "/")
  socketio.on_namespace(socket_ns)
  controller = Controller(app, socket_ns, sw, model)
  model.add_subs(controller)
  sw.begin()
  app.run(debug=True)
  sw.end()
  print("DONE!")
