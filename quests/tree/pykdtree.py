import numpy as np

from .base import TreeNeighbors
from pykdtree.kdtree import KDTree


class TreePyKDTree(TreeNeighbors):
    def __init__(
        self,
        x: np.ndarray,
    ):
        super().__init__(x)
        self.tree = None

    def build(self):
        self.tree = KDTree(self.x)

    def query(self, x: np.ndarray, k: int) -> np.ndarray:
        dij, _ = self.tree.query(x, k=k)
        return dij
