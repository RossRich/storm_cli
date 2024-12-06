#!/bin/python3

from abc import ABC, abstractmethod
from json import load
from typing import Callable, Dict, List, Union
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
from static_data import Templates


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
    self._load = 0.0
    self._current = 0.0

  @property
  def load(self) -> float:
    return self._load

  @property
  def current(self) -> float:
    return self._current

  def set_uart_data(self, data) -> None:
    self.serial_data = data
    self.notify(ObsEvent.NEW_DATA)


class SerialWorker():

  class STATES(IntEnum):
    WAIT = auto()
    CONNECTING = auto()
    READ = auto()
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

  def trs(self, new_state) -> None:
    self._state = new_state

  def _worker_callback(self) -> None:
    STATES = SerialWorker.STATES
    while not self._is_stop.is_set():

      if len(serial.tools.list_ports.comports()) == 0:
        self.trs(STATES.CLOSE)

      if self._state == STATES.WAIT:
        potrs = serial.tools.list_ports.comports()
        if len(potrs) > 0:
          self.trs(STATES.CONNECTING)
      elif self._state == STATES.CONNECTING:
        self.serial_port.port = self.port
        self.serial_port.baudrate = 115200
        try:
          self.serial_port.open()
          self.serial_port.flush()
          self.trs(STATES.READ)
        except Exception as e:
          print("Error: " + str(e))
      elif self._state == STATES.READ:
        try:
          if self.serial_port.in_waiting:
            data = self.serial_port.readline()
            if len(data):
              data = data.decode('utf-8')
              data_list = data.split(" ")
              if len(data_list) > 3:
                self.model.set_uart_data({"state": data_list[0], "load": data_list[1], "current": data_list[2]})
              else:
                print("Bad data")
                self.serial_port.flush()
        except Exception as e:
          print(str(e))
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


def get_serial_ports() -> list:
  serial_ports = serial.tools.list_ports.comports()
  for i in serial_ports:
    print(i)
  return [port.name for port in serial_ports]


class SocketWorkerNamespace(Namespace):
  def __init__(self, model: Model, namespace: Union[str, None] = None) -> None:
    super().__init__(namespace)
    self.model = model

  def on_connect(self):
    print("on_connect")
    self.model.is_client_connected = True
    self.model.notify(ObsEvent.CONNECTION)

  def on_disconnect(self):
    print("on_disconnect")
    self.model.is_client_connected = False
    self.model.notify(ObsEvent.DISCONNECTION)

  def on_my_event(self, data):
    print(data)
    self.emit('my_response', data)

  def update_serial_data(self) -> None:
    self.emit("serial_data", self.model.serial_data)

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
    print(self.model.serial_data)
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
  return render_template(Templates.index, ports=get_serial_ports())


if __name__ == "__main__":
  model = Model()
  sw = SerialWorker(60, model)
  socket_ns = SocketWorkerNamespace(model, "/")
  socketio.on_namespace(socket_ns)
  controller = Controller(app, socket_ns, model)
  model.add_subs(controller)
  sw.start()
  app.run(debug=True)
  sw.shutdown()
  print("DONE!")
