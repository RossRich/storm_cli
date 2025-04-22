from typing import Dict, List
from .msg import DataMsg, SetupMsg
from .socket_worker import ViewClickEvent, ViewData, ViewEvent
from .serial_worker import SerialListener, SerialWorker
from .view import View, ViewListener
from .model import Model


class Presenter(SerialListener, ViewListener):
  def __init__(self, view: View, model: Model, serial_worker: SerialWorker):
    super().__init__()

    self._model = model
    self._view = view
    self._view.set_view_listener(self)

    self.serial_worker = serial_worker
    self.serial_worker.set_listener(self)

  # socket section ------>

  def on_click_event(self, e: ViewClickEvent):
    '''
    socket_view
    '''
    super().on_click_event(e)

  def on_event(self, e: ViewEvent):
    '''
    socket_view
    '''
    super().on_event(e)

    if e == ViewEvent.ON_CONNECTION:
      self._model.is_client_connected = True
      self.on_view_start()
    elif e == ViewEvent.ON_DISCONNECTION:
      self._model.is_client_connected = False
      self.on_view_stop()

  def on_update_conf(self, vd: ViewData) -> None:
    super().on_update_conf(vd)
    print(vd)
    # здесь принимать тип сообщения с параметрами (скорее всего словарь)

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
    '''
    serial cb'
    '''

    super().on_new_conf(cfg)
    self._model.cfg = cfg
    self._view.send_cfg(self._model.cfg)

  def on_new_measurements(self, data: DataMsg) -> None:
    '''
    serial cb
    '''

    super().on_new_measurements(data)
    # self._model.set_uart_data(data)
    self._model.serial_data = data
    self._update_ui()

  def on_new_device(self, dev_list: List[str]):
    super().on_new_device(dev_list)

    if dev_list:
      self._model.devices = dev_list
      self.device_to_view()

  # presenter section ------>

  def _update_ui(self) -> None:
    if self._model.serial_data:
      self._view.send_measurements(self._model.serial_data)

  def device_to_view(self) -> None:
    self._view.set_devices(self._model.devices)

  def connect_to_device(self) -> None:
    if self._model.device in self._model.devices:
      self.serial_worker.connect(self._model.device)
