from collections import defaultdict

from yaml import Dumper, dump
from zoti_yaml import Pos, get_pos


class PrettyDumper(Dumper):
    def repr_defaultdict(self, ddict):
        return self.represent_mapping("dict", {k: v["value"] for k, v in ddict.items()})

    # def repr_PrettyError(self, perror):
    #     return self.represent_mapping(f"!{repr(perror.info)}", perror.messages)


PrettyDumper.add_representer(defaultdict, PrettyDumper.repr_defaultdict)
# PrettyDumper.add_representer(info.YamlErrorWrapper, PrettyDumper.repr_PrettyError)


class ValidationError(Exception):
    """ Raised during the validation of the ZOTI schema. """

    def __init__(self, what):
        self.what = dump(what, Dumper=PrettyDumper, default_flow_style=False)

    def __str__(self):
        return f"\n{self.what}"


class ParseError(Exception):
    def __init__(self, what, pos=None, context="", context_pos=None):
        self.what = what
        self.ctx = context
        self.err_pos = pos
        self.ctx_pos = context_pos
        try:
            self.err_pos = pos.show()
        except Exception:
            pass
        try:
            self.ctx_pos = context_pos.show()
        except Exception:
            pass

    def __str__(self):
        msg = f"{self.ctx}\n" if self.ctx else ""
        msg += f"  {self.ctx_pos}\n" if self.ctx_pos else ""
        msg += f"  {self.err_pos}\n" if self.err_pos else ""
        msg += f"{self.what}"
        return msg


class EntryError(Exception):
    def __init__(self, what, obj=None):
        self.what = what
        self.pos = f"{get_pos(obj).show()}" if get_pos(obj) else ""

    def __str__(self):
        return f"{self.pos}\n{self.what}"


class ScriptError(Exception):
    """Exception handler for pretty errors, possibly containing positional
    information as provided by `ZOTI-YAML <../zoti-yaml/>`_ and rule
    documentation.

    :param what: error message
    :param obj: object causing the error. Will be scanned for positional info.
    :param rule: the rule (i.e., function itself) where error was caused. Will
      be scanned for docstring.

    """

    def __init__(self, what, obj=None, rule=None):
        self.what = what
        self.pos = f"\n{get_pos(obj).show()}" if get_pos(obj) else ""
        self.name = f" during rule '{rule.__name__}':" if rule else ""
        self.doc = (f"\n\nRule documentation:\n{rule.__doc__}"
                    if getattr(rule, "__doc__", None) else "")

    def __str__(self):
        return f"{self.name}\n{self.what}{self.pos}{self.doc}"


class ContextError(Exception):
    """Exception handler for pretty errors that happened within a context
    of another object, possibly containing positional information as
    provided by `ZOTI-YAML <../zoti-yaml/>`_.

    :param what: error message
    :param obj: object causing the error. Will be scanned for positional info.
    :param context: context message
    :param context_obj: object constituting the context of the error. Will be 
       scanned for positional info.

    """

    def __init__(self, what, obj=None, context="", context_obj=None):
        self.what = what
        self.context = context
        self.pos = f"\n{get_pos(obj).show()}" if get_pos(obj) else ""
        self.ctx_pos = f"\ncontext {get_pos(context_obj).show()}" if get_pos(
            context_obj) else ""

    def __str__(self):
        return f"{self.context}{self.ctx_pos}\n{self.what}{self.pos}"
