from .appgraph import AppGraph
from .core import *
from .io import *
from importlib.metadata import distribution

dist = distribution("zoti_graph")

__version__ = dist.version
