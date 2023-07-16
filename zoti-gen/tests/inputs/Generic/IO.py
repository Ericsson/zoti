from dataclasses import dataclass, field
from zoti_gen import read_at, with_schema, Block, Requirement, Template, C_DELIMITERS

file_args = {"module": __name__,
             "filename": "templates.c",
             "delimiters": C_DELIMITERS}


@with_schema(Block.Schema)
@dataclass
class ReadArray(Block):
    """Generic implementation for monitoring a system. Gets outside
    information from the console.
    """

    requirement: Requirement = field(
        default=Requirement({"include": ["stdio.h"]}))

    code: str = field(
        default=Template(
            read_at(**file_args, name="ReadArray.C"),
            parent="code")
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
        default=Template(
            read_at(**file_args, name="PrintArray.C"),
            parent="code")
    )

    def check(self):
        assert "format" in self.param
        assert "size" in self.param
        assert "arg" in self.label
