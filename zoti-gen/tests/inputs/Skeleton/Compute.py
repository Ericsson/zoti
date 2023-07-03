from dataclasses import dataclass, field
from zoti_gen import read_at, with_schema, Block, Requirement, Template, C_DELIMITERS


file_args = {"module": __name__,
             "filename": "templates.c",
             "delimiters": C_DELIMITERS}


@with_schema(Block.Schema)
@dataclass
class ShiftFarm(Block):
    """
    Shift-farm specialized skeleton
    """

    requirement: Requirement = field(
        default=Requirement({"include": ["cutils.h"]}))

    code: str = field(
        default=Template(
            read_at(**file_args, name="ShiftFarm.C"),
            parent="code")
    )

    def check(self):
        # internal iterator (resolved name)
        assert "_it" in self.label

        # auto-bound to 'size1' from placeholder? TODO
        assert "_range" in self.label

        # called template
        assert "f" in [i.placeholder for i in self.instance]


@with_schema(Block.Schema)
@dataclass
class FarmRed_Acc(Block):
    """
    Farm-reduce skeleton with initial element, fused map-reduce kernel function
    and programmable (exposed) size param.
    """

    requirement: Requirement = field(
        default=Requirement({"include": ["cutils.h"]}))

    code: str = field(
        default=Template(
            read_at(**file_args, name="FarmRed_Acc.C"),
            parent="code")
    )

    def check(self):
        # internal iterator (resolved name)
        assert "_it" in self.label

        # auto-bound to 'size1' from placeholder? TODO
        assert "_acc" in self.label

        # label IDs over which '_it' iterates
        assert "iterate_over" in self.param

        # called fused farm-reduce kernel
        assert "f" in [i.placeholder for i in self.instance]
