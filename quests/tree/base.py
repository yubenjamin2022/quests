from abc import ABC
from abc import abstractmethod

import numpy as np


class NeighborsFinder(ABC):
    def __init__(
        self,
        x: np.ndarray,
        **kwargs,
    ):
        self.x = x

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def query(self, x: np.ndarray, k: int):
        pass

    @property
    def n(self):
        return len(self.x)
