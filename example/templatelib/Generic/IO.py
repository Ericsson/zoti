from dataclasses import dataclass, field
from pathlib import Path

from zoti_gen import read_template, with_schema
from zoti_gen.types import Block, Requirement


@with_schema(Block.Schema)
@dataclass
class ReadArray(Block):
    """
    Generic implementation for monitoring a system. Gets outside information from the console.
    """

    requirement: Requirement = field(default=Requirement({"include": ["stdio.h"]}))

    code: str = field(
        default=read_template(Path(__file__).with_name("templates.c"), "ReadArray.C")
    )

    def check(self):
        # print(self.param, self.port)
        assert "format" in self.param
        assert "arg" in self.port
        # assert isinstance(self.port['arg'].type, Array)
        # assert istype_lite(self.port["arg"].type, "Array")


@with_schema(Block.Schema)
@dataclass
class PrintArray(Block):
    """ Generic implementation for monitoring a system. Prints an array to the console. """

    requirement: Requirement = field(default=Requirement({"include": ["stdio.h"]}))

    code: str = field(
        default=read_template(Path(__file__).with_name("templates.c"), "PrintArray.C")
    )

    def check(self):
        assert "format" in self.param
        assert "arg" in self.port
        # assert isinstance(self.port['arg'].type, Array)
        # assert istype_lite(self.port["arg"].type, "Array")
