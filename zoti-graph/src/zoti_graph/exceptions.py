from collections import defaultdict

from yaml import Dumper, dump
from zoti_yaml import Pos


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
        print(pos)
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
