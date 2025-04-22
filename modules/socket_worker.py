from abc import ABC, abstractmethod
from enum import IntEnum, auto, unique
from typing import Any, Dict, List, Union
from flask_socketio import Namespace
from .iview import IView, ViewData, ViewDataSrc


@unique
class ViewEvent(IntEnum):
  ON_CONNECTION = auto()
  ON_DISCONNECTION = auto()


@unique
class ViewClickEvent(IntEnum):
  START_TEST = auto()
  STOP_TEST = auto()
  SETUP_ESC = auto()


class SocketListener(ABC):
  @abstractmethod
  def on_click_event(self, e: ViewClickEvent) -> None:
    pass

  @abstractmethod
  def on_event(self, e: ViewEvent) -> None:
    pass

  @abstractmethod
  def on_submit(self, view_data: ViewData) -> None:
    pass


class SocketView(Namespace, IView):
  def __init__(self, view_ns: Union[str, None] = None) -> None:
    super().__init__(view_ns)
    self._label = f"[{self.__class__.__name__}] "
    self.click_listener: Union[SocketListener, None] = None
    self.event_listener: Union[SocketListener, None] = None

  # объединить
  def add_click_listener(self, listener: SocketListener):
    self.click_listener = listener

  # объединить
  def add_event_listener(self, listener: SocketListener):
    self.event_listener = listener

  def on_connect(self):
    if self.event_listener:
      self.event_listener.on_event(ViewEvent.ON_CONNECTION)

  def on_disconnect(self):
    if self.event_listener:
      self.event_listener.on_event(ViewEvent.ON_DISCONNECTION)

  # сделать общий метод on_get_data, который принимает словарь
  # в нем производить преобразование словаря в viewdata и уже потом вызывать соответствующие
  # методы обработчики

  def on_submit(self, data: Dict[str, Any]) -> bool:
    if not data:
      return False

    try:
      if "src" not in data.keys():
        raise ValueError()

      src = ViewDataSrc(int(data["src"]))

      if src == ViewDataSrc.SELECT_DEVICE:
        vd = ViewData(src, data["data"])
        self.event_listener.on_submit(vd)
      elif src == ViewDataSrc.CONFIGURATION:
        vd = ViewData(src, data["data"])
        self.event_listener.on_submit(vd)
      else:
        print("INVALID SRC")

    except Exception as e:
      print(self._label + str(e))
      return False

    return True

  def on_new_cmd(self, data) -> None:
    self.click_listener.on_click_event(ViewClickEvent.START_TEST)

  def set_measurements(self, data: ViewData):
    super().set_measurements(data)
    self.emit("new_measurements", data.data)

  def set_configuration(self, conf: ViewData):
    super().set_configuration(conf)
    self.emit("new_configuration", conf.data)

  def set_devices(self, devices: List[str]) -> None:
    super().set_devices(devices)
    obj = [{"name": d} for d in devices]
    self.emit("new_devices", obj)
