from zoml.core import Pos


class ModuleError(Exception):
    """Raised when some specific module metadata is missing or other
    reasons why a module cannot be loaded,

    """

    def __init__(self, what, module=None, path=None):
        self.what = what
        self.module = module
        self.path = path

    def __str__(self):
        module = f" '{self.module}'" if self.module else ""
        path = f" ({self.path})" if self.path else ""
        msg = f"Error loading module{module}{path}\n{self.what}"
        return msg


class SearchError(Exception):
    """Raised when a search based on a :class:`zoml.core.TreePath`
    fails.

    """

    def __init__(self, what, path=None, obj=None):
        self.what = what
        self.path = path
        self.obj = obj

    def __str__(self):
        keys = f" among {list(self.obj.keys())}" if isinstance(
            self.obj, dict) else ""
        path = f" (in path '{self.path}')"
        return f"{self.what}{path}{keys}"


class MarkedError(Exception):
    """Generic error enhanced with positional information."""

    def __init__(self, what, pos=None):
        self.what = what
        self.pos = pos.show() if isinstance(pos, Pos) else pos

    def __str__(self):
        pos = self.pos if self.pos else ""
        return f"{pos}\n{self.what}"
