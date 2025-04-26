from abc import ABC, abstractmethod
from typing import Any, List, Union
from .msg import DataMsg, SetupMsg
from .iview import IView, ViewData, ViewDataSrc
from .socket_worker import ViewEvent, SocketListener, SocketView


class ViewListener(ABC):
  @abstractmethod
  def on_click_event(self, e) -> None:
    pass

  @abstractmethod
  def on_event(self, e: ViewEvent) -> None:
    pass

  @abstractmethod
  def on_select_device(self, dev: str) -> None:
    pass

  @abstractmethod
  def on_update_conf(self, vd: ViewData) -> None:
    pass


class View(IView, SocketListener):
  def __init__(self, socket: SocketView):
    super().__init__()
    self.socket_ns = socket
    self.socket_ns.add_click_listener(self)
    self.socket_ns.add_event_listener(self)
    self.view_listener: Union[None, ViewListener] = None

  def set_view_listener(self, vl: ViewListener):
    self.view_listener = vl

  def on_click_event(self, e):
    super().on_click_event(e)
    if self.view_listener:
      self.view_listener.on_click_event(e)

  def on_event(self, e: ViewEvent):
    super().on_event(e)
    if self.view_listener:
      self.view_listener.on_event(e)

  def on_submit(self, view_data: ViewData) -> None:
    super().on_submit(view_data)
    if self.view_listener:
      if view_data.src == ViewDataSrc.SELECT_DEVICE:
        di = view_data.data["name"]
        self.view_listener.on_select_device(di)
      elif view_data.src == ViewDataSrc.CONFIGURATION:
        self.view_listener.on_update_conf(view_data)

  def send_cfg(self, cfg: SetupMsg) -> None:
    if cfg.to_dict():
      vd = ViewData(ViewDataSrc.CONFIGURATION, cfg.d)
      self.set_configuration(vd)

  def send_measurements(self, data: DataMsg) -> None:
    if data.to_dict():
      vd = ViewData(ViewDataSrc.MEASUREMENTS, data.d)
      self.set_measurements(vd)

  def set_configuration(self, conf: ViewData):
    super().set_configuration(conf)
    self.socket_ns.set_configuration(conf)

  def set_measurements(self, data: ViewData):
    super().set_measurements(data)
    self.socket_ns.set_measurements(data)

  def set_devices(self, devices: List[str]):
    super().set_devices(devices)
    self.socket_ns.set_devices(devices)
