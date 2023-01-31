import pkgutil
import re
from typing import Set

from marshmallow import post_load


def with_schema(schema_base_class):
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


def read_template(modname: str, filename: str, name: str,
                  delimiters=("\\ *Template: *{name}", "\\ *End: *{name}")) -> str:
    """Returns a template written in a (possibly formatted) external
    source file found at ``path``. A source file may contain multiple
    templates, hence this method returns only the one between
    ``delimiter`` for ``name``. Delimiters are formatted regular
    expressions marking the beginning and end of the template.

    Check the documentation (TBA) for more details on how to
    write templates in their own source file.

    """
    begin = delimiters[0].format(name=name)
    end = delimiters[1].format(name=name)
    m = re.compile(r"%s(.*?)%s" % (begin, end), re.S)

    textfile = pkgutil.get_data(modname, filename)
    if textfile is None:
        msg = "Cannot load file '{filename}' relative to '{modname}'"
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
