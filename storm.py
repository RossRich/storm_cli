#!/bin/python3

from abc import ABC, abstractmethod
from ctypes import Structure, c_bool, c_float, c_int
from json import load
import queue
from typing import Any, Callable, Dict, List, Union
from enum import IntEnum, auto, unique
from threading import Event, Thread
import time
from unittest.mock import seal
import serial
from flask import Flask, abort, redirect, url_for
from flask import render_template
from flask_socketio import Namespace, SocketIO, emit
import serial.tools
import serial.tools.list_ports
from serial.tools.list_ports_common import ListPortInfo
from static_data import Templates

DEBUG_ENABLED = True


def debug_msg(msg):
  global DEBUG_ENABLED
  if DEBUG_ENABLED:
    print(msg)


class SerialMsg():
  DATA_LEN = 25
  START_COND = '$'
  END_COND = '\n'

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
    self.data = '$' + self.data.split('$')[-1]
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
      self.d["weight"] = self.data_list[1]
      self.d["current"] = self.data_list[2]
      self.d["voltage"] = self.data_list[3]
      self.d["pwm"] = self.data_list[4]


@unique
class ObsEvent(IntEnum):
  CONNECTION = auto()
  DISCONNECTION = auto()
  NEW_DATA = auto()


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
    self.serial_data: Dict[str, float] = {}
    self.is_client_connected = False
    self.is_port_opened = False
    self.ports: List[ListPortInfo] = []

  def set_port(self, port: Union[List, ListPortInfo]) -> None:
    if isinstance(port, ListPortInfo):
      if port not in self.ports:
        self.ports

  def set_uart_data(self, data) -> None:
    self.serial_data = data
    self.notify(ObsEvent.NEW_DATA)


class SerialWorker():
  class STATES(IntEnum):
    WAIT = auto()
    CONNECTING = auto()
    READ = auto()
    PARSE = auto()
    CMD = auto()
    CLOSE = auto()

  def __init__(self, rate: int, model: Model) -> None:
    self._is_stop = Event()
    self._is_stop.clear()
    self._rate = 1.0 / rate
    self.worker = Thread(name="serial_worker",
                         target=self._worker_callback)
    self._timer = time.monotonic()
    self._state = SerialWorker.STATES.WAIT
    self.serial_port = serial.Serial()
    self.model = model
    self.port = "/dev/ttyACM0"
    self.msg = SerialMsg()
    self.ports = []

  def trs(self, new_state) -> None:
    self._state = new_state

  def _worker_callback(self) -> None:
    STATES = SerialWorker.STATES
    while not self._is_stop.is_set():
      if self._state == STATES.WAIT:
        self.ports = serial.tools.list_ports.comports()

        if len(self.ports) > 0:
          self.trs(STATES.CONNECTING)
      elif self._state == STATES.CONNECTING:
        self.serial_port.port = self.port
        self.serial_port.baudrate = 115200
        try:
          self.serial_port.open()
          self.trs(STATES.READ)
        except Exception as e:
          print("Error: " + str(e))
      elif self._state == STATES.READ:
        try:
          if self.serial_port.in_waiting > 5:
            self.msg.data = self.serial_port.read_until().decode()
            # print(self.msg)
            if self.msg.find_start() and self.msg.find_end() and self.msg.is_data_exist():
              self.trs(STATES.PARSE)
        except Exception as e:
          print(str(e))

      elif self._state == STATES.PARSE:
        self.msg.parse()
        self.msg.to_dict()
        # print(self.msg.d)
        self.model.set_uart_data(self.msg.d)
        self.trs(STATES.READ)

      elif self._state == STATES.CLOSE:
        try:
          self.serial_port.close()
          self.trs(STATES.WAIT)
          print("Port close")
        except:
          pass

      time.sleep(self._rate)

  def start(self) -> None:
    self.worker.start()

  def shutdown(self) -> None:
    self._is_stop.set()
    self.serial_port.close()
    self.worker.join()


class SocketWorkerNamespace(Namespace):
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

  def on_my_event(self, data):
    debug_msg(data)
    self.emit('my_response', data)

  def update_serial_data(self) -> bool:
    self.emit("serial_data", self.model.serial_data)

  def update_ports_list(self, ports: List[ListPortInfo]) -> bool:
    if not self.model.is_client_connected:
      debug_msg(self._label + "Client not connected")
      return False

    debug_msg("Update ports")

  def request(self, data):
    pass
    # self.model.serial_data = data
    # print("uart data:", data)


class Controller(Subscriber):
  def __init__(self, flask_app: Flask, socket: SocketWorkerNamespace, model: Model) -> None:
    self._flask_app = flask_app
    self._socket = socket
    self.model = model
    self.serial = serial

    self.event_handlers: Dict[ObsEvent, Callable[[ObsEvent], None]] = {
      ObsEvent.CONNECTION: self.on_connection,
      ObsEvent.DISCONNECTION: self.on_disconnection,
      ObsEvent.NEW_DATA: self.new_data
    }

  def on_connection(self, ignore) -> None:
    print("New connection")

  def on_disconnection(self, ignore) -> None:
    print("Disconnection")

  def new_data(self, i) -> None:
    self._socket.update_serial_data()

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
  model = Model()
  sw = SerialWorker(30, model)
  socket_ns = SocketWorkerNamespace(model, "/")
  socketio.on_namespace(socket_ns)
  controller = Controller(app, socket_ns, model)
  model.add_subs(controller)
  sw.start()
  app.run(debug=True)
  sw.shutdown()
  print("DONE!")
