from enum import EnumMeta, Enum
from functools import wraps
from pprint import pformat
from typing import Any, Dict
from pathlib import PurePosixPath
import json


def default_init(init):
    import inspect

    def_args = inspect.signature(init).parameters
    def_arg_names = list(def_args.keys())[1:]

    @wraps(init)
    def new_init(self, *args, **kwargs):
        init_args = {**dict(zip(def_arg_names, args)), **kwargs}
        for name, def_value in def_args.items():
            if name == "self":
                continue
            if name in init_args:
                setattr(self, name, init_args[name])
            elif def_value.default is not inspect.Parameter.empty:
                setattr(self, name, def_value.default)
            elif def_value.kind is not inspect.Parameter.VAR_KEYWORD:
                raise TypeError(f"__init__() missing required argument: '{name}'")
        init(self, *args, **kwargs)

    return new_init


def default_repr(repr):
    """Decorates a ``__repr__`` method for classes without an explicit
    one. Useful for quick debug printouts without much boilerplate.
    Usage::

        @default_repr
        def __repr__(self):
            pass

    """

    @wraps(repr)
    def new_repr(self):
        name = type(self).__name__
        indent = " " * (len(name) + 1)
        # idx, mems = (0, [])
        newrep = pformat(self.__dict__).split("\n")
        return (
            f"{name}({newrep[0]}\n"
            + "\n".join([f"{indent}{ln}" for ln in newrep[1:]])
            + "\n)"
        )

    return new_repr


def unique_name(name, pool, modifier=lambda n, string: n + string):
    idx, newname = (0, name)
    # print(name, pool)
    while newname in pool:
        newname = modifier(name, str(idx))
        idx += 1
    return newname


class SearchableEnum(EnumMeta):
    def __contains__(cls, item):
        try:
            cls[item.upper()]
        except KeyError:
            return False
        return True

    def __getitem__(cls, item):
        return super(SearchableEnum, cls).__getitem__(item.upper())


class GenericJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            pass
        cls = type(obj)
        isenum = False
        if isinstance(obj, Enum):
            data = obj.name
            isenum = True
        elif isinstance(obj, PurePosixPath):
            data = obj.as_posix()
        elif not hasattr(cls, '__json_encode__'):
            data = obj.__dict__
        else:
            data = obj.__json_encode__
        result = {
            '__enum__': isenum,
            '__custom__': True,
            '__module__': cls.__module__,
            '__name__': cls.__name__,
            'data': data
        }
        return result


def GenericJSONDecoderHook(result):
    if not isinstance(result, dict) or not result.get('__custom__', False):
        return result
    if result['__name__'] == "PurePosixPath":
        return PurePosixPath(result['data'])
    import sys
    module = result['__module__']
    if module not in sys.modules:
        __import__(module)
    cls = getattr(sys.modules[module], result['__name__'])
    if result['__enum__']:
        return cls[result['data']]
    if hasattr(cls, '__json_decode__'):
        return cls.__json_decode__(result['data'])
    instance = cls.__new__(cls)
    instance.__dict__.update(result['data'])
    return instance
