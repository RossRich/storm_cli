from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List


class ViewDataSrc(IntEnum):
  CONFIGURATION = 0
  SELECT_DEVICE = 1
  MEASUREMENTS = 2


@dataclass
class ViewData():
  src: ViewDataSrc
  data: Dict[str, Any]


class IView(ABC):
  @abstractmethod
  def set_measurements(self, vd: ViewData) -> None:
    pass

  @abstractmethod
  def set_configuration(self, vd_conf: ViewData) -> None:
    pass

  @abstractmethod
  def set_devices(self, devices: List[str]) -> None:
    pass
