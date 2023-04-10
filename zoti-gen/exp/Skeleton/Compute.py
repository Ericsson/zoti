from dataclasses import dataclass, field
from pathlib import Path

from zoti_gen import read_template, with_schema, Block, Requirement


@with_schema(Block.Schema)
@dataclass
class ShiftFarm(Block):
    """
    Shift-farm specialized skeleton
    """

    requirement: Requirement = field(default=Requirement({"include": ["cutils.h"]}))

    code: str = field(
        default=read_template(__name__, "templates.c", "ShiftFarm.C")
    )

    def check(self):
        # internal iterator (resolved name)
        assert "_it" in self.label
        # assert isinstance(self.label['_it'].type, Primitive)
        # assert istype_lite(self.label["_it"].type, "Primitive")

        # auto-bound to 'size1' from placeholder? TODO
        assert "_range" in self.label
        # assert isinstance(self.label['_range'].type, Primitive)
        # assert istype_lite(self.label["_range"].type, "Primitive")

        # label IDs over which '_it' iterates
        # assert 'iterate_over' in self.param
        # for p in self.param['iterate_over']:
        #     assert isinstance(self.label[p].type, Array)

        # called template
        assert "f" in [i.placeholder for i in self.instance]


@with_schema(Block.Schema)
@dataclass
class FarmRed_Acc(Block):
    """
    Farm-reduce skeleton with initial element, fused map-reduce kernel function
    and programmable (exposed) size param.
    """

    requirement: Requirement = field(default=Requirement({"include": ["cutils.h"]}))

    code: str = field(
        default=read_template(__name__, "templates.c", "FarmRed_Acc.C")
    )

    def check(self):
        # internal iterator (resolved name)
        assert "_it" in self.label
        # assert isinstance(self.label['_it'].type, Primitive)
        # assert istype_lite(self.label["_it"].type, "Primitive")

        # auto-bound to 'size1' from placeholder? TODO
        assert "_acc" in self.label

        # label IDs over which '_it' iterates
        assert "iterate_over" in self.param
        # for p in self.param['iterate_over']:
        #     assert isinstance(self.label[p].type, Array)

        # called fused farm-reduce kernel
        assert "f" in [i.placeholder for i in self.instance]
