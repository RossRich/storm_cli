from abc import ABC
from enum import IntEnum, auto, unique
from typing import List


@unique
class ObsEvent(IntEnum):
  CONNECTION = auto()
  DISCONNECTION = auto()
  NEW_DATA = auto()
  NEW_PORT = auto()
  SELECT_PORT = auto()
  NEW_CMD = auto()
  UPDATE_SETUP = auto()


class Subscriber(ABC):
  def __init__(self) -> None:
    pass

  def update(self, event: ObsEvent) -> None:
    pass


class Publisher(ABC):
  def __init__(self) -> None:
    self._subs: List[Subscriber] = []

  def add_subs(self, subscriber: Subscriber) -> None:
    self._subs.append(subscriber)

  def notify(self, event: ObsEvent) -> None:
    for s in self._subs:
      s.update(event)
