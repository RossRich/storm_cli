#!/bin/python3

from enum import IntEnum, auto
from threading import Event, Thread
import time
import serial
from flask import Flask, abort, redirect, url_for
from flask import render_template
from flask_socketio import Namespace, SocketIO, emit
import serial.tools
import serial.tools.list_ports

from static_data import Templates

class SerialWorker(Namespace):

  class STATES(IntEnum):
    WAIT = auto()
    CONNECTING = auto()
    READ = auto()
    CMD = auto()
    CLOSE = auto()

  def __init__(self, rate: int) -> None:
    super().__init__("/")
    
    self._is_stop = Event()
    self._is_stop.clear()
    self._rate = 1.0 / rate
    self.worker = Thread(name="serial_worker", target=self._worker_callback)
    self._timer = time.monotonic()
    self._state = SerialWorker.STATES.WAIT
    self.socketio = socketio
    self.serial_port = serial.Serial()

  def on_connect(self):
    print("on_connect")

  def on_disconnect(self):
    print("on_disconnect")

  def on_my_event(self, data):
    print(data)
    emit('my_response', data)
  
  def on_uart(self, data):
    print("uart data:", data)

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
          ports_list = [port.name for port in potrs]
          socketio.emit("uart", {"event": "new_port", "data": ports_list})
          self.trs(STATES.CONNECTING)
      elif self._state == STATES.CONNECTING:
        self.serial_port.port = "/dev/ttyACM0"
        self.serial_port.baudrate = 115200
        try:
          self.serial_port.open()
          self.trs(STATES.READ)
        except Exception as e:
          print("Error: " + str(e))
      elif self._state == STATES.READ:
        data = self.serial_port.readline()
        if len(data):
          print(data.decode('utf-8'))
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
  def on_connect(self):
    print("on_connect")

  def on_disconnect(self):
    print("on_disconnect")

  def on_my_event(self, data):
    print(data)
    emit('my_response', data)


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
  # main_ns = SocketWorkerNamespace("/")
  sw = SerialWorker(1)
  socketio.on_namespace(sw)
  sw.start()
  app.run(debug=True)
  sw.shutdown()
  print("DONE!")
