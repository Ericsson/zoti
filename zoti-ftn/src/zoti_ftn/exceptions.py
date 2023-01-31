from collections import defaultdict
from copy import deepcopy
from typing import Optional

import yaml
from marshmallow import ValidationError
from zoti_yaml import get_pos


class ParseError(Exception):
    def __init__(self, what, path=None, **kwargs):
        self.what = what
        self.path = path

    def __str__(self):
        msg = f' in file "{self.path}"' if self.path else ""
        msg += f"\n{self.what}"
        return msg


class FtnError(Exception):
    def __init__(self, what, uid=None, type=None, info=None, **kwargs):
        self.what = what
        self.name = uid
        self.type = type
        self.pos = info

    def __str__(self):
        msg = "for"
        msg += f" '{self.name}'" if self.name else ""
        msg += " of" if self.name and self.type else ""
        msg += f" type '{self.type}'" if self.type else ""
        msg += f"\n  in {self.pos}" if self.pos else ""
        msg += (
            f"\n{self.what.__class__.__name__}: {self.what}"
            if isinstance(self.what, Exception)
            else f"\n{self.what}"
        )
        return msg


class PrettyDumper(yaml.SafeDumper):
    def repr_defaultdict(self, ddict):
        return self.represent_mapping("dict", {k: v["value"] for k, v in ddict.items()})

    # def repr_prettyinfo(self, info):
    #     return self.represent_scalar("!pos", repr(info))


PrettyDumper.add_representer(defaultdict, PrettyDumper.repr_defaultdict)
# PrettyDumper.add_representer(Info, PrettyDumper.repr_prettyinfo)


class PrettyValidationError(ValidationError):
    def __init__(self, arg, node=None, **kwargs):
        if isinstance(arg, ValidationError):
            self.__dict__ = deepcopy(arg.__dict__)
        else:
            super(PrettyValidationError, self).__init__(arg, **kwargs)
        # info = node.get(ATTR_INFO) if node is not None else None
        # print(yaml.dump(self.messages, Dumper=PrettyDumper))
        info = get_pos(node)
        if info and isinstance(self.messages, list):
            self.messages.insert(0, repr(info))
        elif info and isinstance(self.messages, dict):
            self.messages["@"] = repr(info)

    def __str__(self):
        msg = yaml.dump(self.messages, Dumper=PrettyDumper)
        return "\n" + msg
