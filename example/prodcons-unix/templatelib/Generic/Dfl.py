from dataclasses import dataclass, field
from pathlib import Path

from zoti_gen import read_at, with_schema, Block, Requirement, Template, C_DELIMITERS

file_args = {"module": __name__,
             "filename": "dfl.c",
             "delimiters": C_DELIMITERS}


@with_schema(Block.Schema)
@dataclass
class Main(Block):

    code: Template = field(
        default=Template(read_at(**file_args, name="Main.C"), parent="code"))

    def check(self):
        pass


@with_schema(Block.Schema)
@dataclass
class CfgInport(Block):

    requirement: Requirement = field(
        default=Requirement(
            {"include": ["<stdio.h>", "<sys/types.h>", "<sys/socket.h>"]})
    )

    code: Template = field(
        default=Template(
            read_at(**file_args, name="CFG_inport.C"),
            parent="code")
    )

    prototype: Template = field(
        default=Template(
            'int {{name}}(char * name, int32_t ip_port) { {{ placeholder["code"] }} }',
            parent="prototype")
    )


@with_schema(Block.Schema)
@dataclass
class CfgOutport(Block):

    requirement: Requirement = field(
        default=Requirement(
            {"include": ["<stdio.h>", "<sys/types.h>", "<sys/socket.h>"]})
    )

    code: Template = field(
        default=Template(
            read_at(**file_args, name="CFG_outport.C"),
            parent="code")
    )

    prototype: Template = field(
        default=Template(
            'int {{name}}(char* name, char* ip_addr, int32_t ip_port) { {{ placeholder["code"] }} }',
            parent="prototype")
    )


@with_schema(Block.Schema)
@dataclass
class CfgAtom(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>"]})
    )

    code: Template = field(
        default=Template(
            read_at(**file_args, name="CFG_atom.C"),
            parent="code")
    )

    prototype: Template = field(
        default=Template(
            'int {{name}}(size_t len, char * name, uint32_t id_nr) { {{ placeholder["code"] }} }',
            parent="prototype")
    )


@with_schema(Block.Schema)
@dataclass
class UdpReceive(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>"]})
    )

    code: str = field(
        default=Template(
            read_at(**file_args, name="UdpReceive.C"),
            parent="code")
    )

    def check(self):
        assert "size" in self.label
        assert "socket" in self.label
        assert "ram" in self.label


@with_schema(Block.Schema)
@dataclass
class UdpSend(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>"]})
    )

    code: str = field(
        default=Template(
            read_at(**file_args, name="UdpSend.C"),
            parent="code")
    )

    def check(self):
        assert "socket" in self.label
        assert "data" in self.label


@with_schema(Block.Schema)
@dataclass
class TimerReceive(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<inttypes.h>"]})
    )

    code: str = field(
        default=Template(
            read_at(**file_args, name="TimerReceive.C"),
            parent="code")
    )

    def check(self):
        assert "timerrecv" in self.label
        assert "timestamp" in self.label
