import pkgutil
import re
from typing import Set, Tuple

from marshmallow import post_load


def with_schema(schema_base_class):
    """Wrapper which creates a sub-class ``Schema`` under the current
    class, as a (default) child of *schema_base_class*

    Example usage:

    .. code-block:: python

        @with_schema(Block.Schema)
        @dataclass
        class ReadArray(Block):
            pass

    will create a class ``ReadArray.Schema`` which is used whenever
    instantiating this class with data from the input specification
    file.

    """

    def Inner(cls):
        class Wrapper:
            def __init__(self, *args, **kwargs):
                self.wrap = cls(*args, **kwargs)

            class Schema(schema_base_class):
                @post_load
                def make(self, data, **kwargs):
                    return cls(**data)

        return Wrapper

    return Inner


# def peek_line(f):
#     pos = f.tell()
#     line = f.readline()
#     f.seek(pos)
#     return line

C_DELIMITERS = ("\\ *Template: *{name}", "\\ *End: *{name}")
VHDL_DELIMITERS = ("-- *Template: *{name}", "-- *End: *{name}")


def read_at(module: str, filename: str, name: str,
            delimiters: Tuple[str, str] = C_DELIMITERS) -> str:
    """Returns a template string from a (possibly formatted) external
    source file. A source file may contain multiple templates, hence
    this method returns only the one between ``delimiter`` for
    ``name``.

    :arg module: name of Python module relative to which the source
        file is found (e.g. can use ``__name__`` if it is in the same
        path as the current file)

    :arg filename: full name of the source file, including extension.

    :arg name: name of the current component, used as delimiter marker
       in case multiple components are defined in the same file.

    :arg delimiters: tuple containing the begin and end marker for the
        issued template, formatted as regular expressions where
        ``{name}`` is replaced with **name**.

    """
    begin = delimiters[0].format(name=name)
    end = delimiters[1].format(name=name)
    m = re.compile(r"%s(.*?)%s" % (begin, end), re.S)

    textfile = pkgutil.get_data(module, filename)
    if textfile is None:
        msg = "Cannot load file '{filename}' relative to '{module}'"
        raise IOError(msg)
    text = m.search(textfile.decode())
    if text:
        t = text.group(1)
    else:
        msg = f"Did not find template for '{name}' in file {filename}"
        raise IOError(msg)
    return t


def qualname(o):
    klass = o.__class__
    module = klass.__module__
    if module == "builtins":
        return klass.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + klass.__qualname__


def uniqueName(name: str, namespace: Set[str], update: bool = True) -> str:
    """Returns a unique name in the given namespace.
    Updates namespace if ``update`` is set.
    """
    idx = 0
    newName = name
    while newName in namespace:
        newName = name + str(idx)
        idx += 1
    if update:
        namespace.add(newName)
    return newName
