from typing import List
from .iview import ViewDataSrc
from .msg import DataMsg, MsgType, SerialMsg, SetupMsg
from .socket_worker import ViewClickEvent, ViewData, ViewEvent
from .serial_worker import SerialCmd, SerialListener, SerialWorker
from .view import View, ViewListener
from .model import Model


class Presenter(SerialListener, ViewListener):
  def __init__(self, view: View, model: Model, serial_worker: SerialWorker):
    super().__init__()
    self._label = f"[{self.__class__.__name__}] "

    self._model = model
    self._view = view
    self._view.set_view_listener(self)

    self.serial_worker = serial_worker
    self.serial_worker.set_listener(self)

    self.verbose = False

  def log(self, msg: str) -> None:
    if self.verbose:
      print(self._label + msg)

  # socket section ------>

  def on_click_event(self, e: ViewClickEvent):
    super().on_click_event(e)

    self.log(e.name)

    if e == ViewClickEvent.STOP_TEST:
      self.stop_test()
    elif e == ViewClickEvent.START_TEST:
      self.start_test()
    elif e == ViewClickEvent.SETUP_ESC:
      self.setup_esc()
    elif e == ViewClickEvent.GET_SETUP:
      self.get_setup()
    else:
      pass

  def on_event(self, e: ViewEvent):
    super().on_event(e)

    self.log(e.name)

    if e == ViewEvent.ON_CONNECTION:
      self._model.is_client_connected = True
      self.on_view_start()
    elif e == ViewEvent.ON_DISCONNECTION:
      self._model.is_client_connected = False
      self.on_view_stop()

  def on_update_conf(self, vd: ViewData) -> None:
    super().on_update_conf(vd)
    if self._model.is_port_opened and vd.src == ViewDataSrc.CONFIGURATION:
      self._model.cfg = {"id": self._model.setup_id} | vd.data
      self._model.setup_id += 1
      self.setup_device()

  def on_select_device(self, dev: str) -> None:
    super().on_select_device(dev)
    self._model.device = dev
    self.connect_to_device()

  def on_view_start(self) -> None:
    self.serial_worker.scan_ports()

  def on_view_stop(self) -> None:
    self.serial_worker.disconnect()
    self._model.devices = []
    self._model.device = ""

  # serial section ------>

  def on_new_conf(self, cfg: SetupMsg):
    super().on_new_conf(cfg)
    if cfg.to_dict():
      self._model.cfg = cfg.d
      self.update_ui_cfg()

  def on_new_measurements(self, data: DataMsg) -> None:
    super().on_new_measurements(data)
    if data.to_dict():
      self._model.measurements = data.d
      self.update_ui()

  def on_new_device(self, dev_list: List[str]):
    super().on_new_device(dev_list)

    if dev_list:
      self._model.devices = dev_list
      self.device_to_view()

  def on_open(self):
    super().on_open()
    self.log("Serial port opened")
    self._model.is_port_opened = True
    self.get_setup()

  def on_close(self):
    super().on_close()
    self.log("Serial port closed")
    self._model.is_port_opened = False

  # presenter section ------>

  def update_ui(self) -> None:
    if self._model.measurements:
      vd = ViewData(ViewDataSrc.MEASUREMENTS, self._model.measurements)
      self._view.set_measurements(vd)

  def update_ui_cfg(self) -> None:
    if self._model.cfg:
      vd = ViewData(ViewDataSrc.CONFIGURATION, self._model.cfg)
      self._view.set_configuration(vd)

  def device_to_view(self) -> None:
    self._view.set_devices(self._model.devices)

  def connect_to_device(self) -> None:
    if self._model.device in self._model.devices:
      self.serial_worker.connect(self._model.device)

  def setup_device(self) -> None:
    if self._model.cfg:
      sm = SerialMsg()
      sm.fill(self._model.cfg, MsgType.SETUP)
      self.serial_worker.write(sm)

  def start_test(self) -> None:
    if self._model.is_port_opened:
      sm = SerialMsg(10)
      sm.fill({"cmd": SerialCmd.START_TEST.value}, MsgType.CMD)
      self.serial_worker.write(sm)

  def stop_test(self) -> None:
    if self._model.is_port_opened:
      sm = SerialMsg(10)
      sm.fill({"cmd": SerialCmd.STOP_TEST.value}, MsgType.CMD)
      self.serial_worker.write(sm)

  def setup_esc(self) -> None:
    if self._model.is_port_opened:
      sm = SerialMsg(10)
      sm.fill({"cmd": SerialCmd.SETUP_ESC.value}, MsgType.CMD)
      self.serial_worker.write(sm)

  def get_setup(self) -> None:
    if self._model.is_port_opened:
      sm = SerialMsg(10)
      sm.fill({"cmd": SerialCmd.GET_SETUP.value}, MsgType.CMD)
      self.serial_worker.write(sm)
