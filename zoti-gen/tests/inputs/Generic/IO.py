from dataclasses import dataclass, field
from zoti_gen import read_template, with_schema, Block, Requirement


@with_schema(Block.Schema)
@dataclass
class ReadArray(Block):
    """Generic implementation for monitoring a system. Gets outside
    information from the console.
    """

    requirement: Requirement = field(
        default=Requirement({"include": ["stdio.h"]}))

    code: str = field(
        default=read_template(__name__, "templates.c", "ReadArray.C")
    )

    def check(self):
        assert "format" in self.param
        assert "size" in self.param
        assert "arg" in self.label


@with_schema(Block.Schema)
@dataclass
class PrintArray(Block):
    """Generic implementation for monitoring a system. Prints an array to
    the console.
    """

    requirement: Requirement = field(
        default=Requirement({"include": ["stdio.h"]}))

    code: str = field(
        default=read_template(__name__, "templates.c", "PrintArray.C")
    )

    def check(self):
        assert "format" in self.param
        assert "size" in self.param
        assert "arg" in self.label
