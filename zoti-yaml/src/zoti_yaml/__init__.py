from .core import INFO, POS, Pos, PosStack, Ref, attach_pos, get_pos
from .exceptions import MarkedError, ModuleError, SearchError
from .module import Module
from .project import Project
from .loader import LoaderWithInfo

from importlib.metadata import distribution
__distribution__ = distribution("zoti_yaml")
__version__ = __distribution__.version
__fullname__ = __distribution__.name + "-" + __distribution__.version
