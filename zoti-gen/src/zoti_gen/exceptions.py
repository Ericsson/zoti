import logging as log
from collections import defaultdict
from typing import Dict

from yaml import Dumper, dump
from zoti_yaml import get_pos
from pprint import pformat


class PrettyDumper(Dumper):
    def repr_defaultdict(self, ddict):
        print(ddict)
        return self.represent_mapping(
            "dict", {k: f"({where}) {''.join(what)}"
                     for k, v in ddict.items()
                     for where, what in v.items()})


PrettyDumper.add_representer(defaultdict, PrettyDumper.repr_defaultdict)


class ValidationError(Exception):
    """ Raised during the validation of the ZOTI schema. """

    def __init__(self, what, obj=None, **kwargs):
        self.what = dump(what, Dumper=PrettyDumper, default_flow_style=False)
        self.pos = get_pos(obj).show() if get_pos(obj) else ""

    def __str__(self):
        return f"{self.pos}\n{self.what}"


class ParseError(Exception):
    def __init__(self, what, obj=None, **kwargs):
        self.what = what
        self.pos = get_pos(obj).show() if get_pos(obj) else ""

    def __str__(self):
        return f"{self.pos}\n{self.what}"


class ModelError(Exception):
    def __init__(self, what, name=None, obj=None, **kwargs):
        self.what = what
        self.name = f"for '{name}' " if name else ""
        # self.pos = Pos(*pos).show() if pos else ""
        self.pos = get_pos(obj).show() if get_pos(obj) else ""

    def __str__(self):
        return f"{self.name}{self.pos}\n{self.what}"


class TemplateError(Exception):
    """ Wraps a Jinja template error into a friendlier message. """

    def __init__(
            self,
            template: str,
            context: Dict,
            err_line: int,
            err_string: str,
            msg: str = "Jinja raised error when processing template",
            info=None,
            parent=None,
    ):
        self.template = str(template)
        self.err_line = err_line
        self.err = err_string
        self.message = msg + f" in node '{parent}'" if parent else ""
        self.pos = f"\n  {info.show()}" if info else ""
        self.context = pformat(context)

    def __str__(self):
        temp_lines = self.template.splitlines()
        if len(temp_lines) < 2:
            err_str = f"{self.template}"
        else:
            mark = [
                (" ", self.err_line - 2),
                ("!", self.err_line - 1),
                (" ", self.err_line),
            ]
            err_lines = [(pre, n)
                         for pre, n in mark
                         if n >= 0 and n < len(temp_lines)
                         ]
            err_str = "".join([
                f"{str(n):>3}{pre}# {temp_lines[n]}\n"
                for pre, n in err_lines
            ])
        ctx = f"\n Passed context:\n{self.context}" if log.root.level < log.WARN else ""
        msg = f"{self.message}{self.pos}\n{err_str}\n{self.err}{ctx}"
        return msg
