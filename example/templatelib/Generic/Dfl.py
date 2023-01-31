from dataclasses import dataclass, field
from pathlib import Path

from zoti_gen import read_template, with_schema, Block, Requirement, TemplateFun


@with_schema(Block.Schema)
@dataclass
class Main(Block):
    
    code: str = field(
        # default=read_template(Path(__file__).with_name("dfl.c"), "Main.C")
        default=read_template(__name__, "dfl.c", "Main.C")
    )

    def check(self):
        # print(self.param, self.label)
        # assert "format" in self.param
        # assert "arg" in self.label
        # assert isinstance(self.label['arg'].type, Array)
        # assert istype_lite(self.label["arg"].type, "Array")
        pass


@with_schema(Block.Schema)
@dataclass
class CfgInport(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>", "<sys/types.h>", "<sys/socket.h>"]})
    )

    code: str = field(
        # default=read_template( Path(__file__).with_name("dfl.c"), "CFG_inport.C")
        default=read_template(__name__, "dfl.c", "CFG_inport.C")
    )

    prototype: TemplateFun = field(
        default=TemplateFun("prototype", "name", 'int $name(char * name, int32_t ip_port) { {{ placeholder["code"] }} }')
    )

    def check(self):
        # print(self.param, self.label)
        # assert "format" in self.param
        # assert "arg" in self.label
        # assert isinstance(self.label['arg'].type, Array)
        # assert istype_lite(self.label["arg"].type, "Array")
        pass


@with_schema(Block.Schema)
@dataclass
class CfgOutport(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>", "<sys/types.h>", "<sys/socket.h>"]})
    )
    
    code: TemplateFun = field(
        # default=read_template(Path(__file__).with_name("dfl.c"), "CFG_outport.C")
        default=read_template(__name__, "dfl.c", "CFG_outport.C")
    )

    prototype: TemplateFun = field(
        default=TemplateFun("prototype", "name",
                            'int $name(char * name, char * ip_addr, int32_t ip_port) { {{ placeholder["code"] }} }')
    )

    def check(self):
        # print(self.param, self.label)
        # assert "format" in self.param
        # assert "arg" in self.label
        # assert isinstance(self.label['arg'].type, Array)
        # assert istype_lite(self.label["arg"].type, "Array")
        pass


@with_schema(Block.Schema)
@dataclass
class CfgAtom(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>"]})
    )
    
    code: str = field(
        # default=read_template(Path(__file__).with_name("dfl.c"), "CFG_atom.C")
        default=read_template(__name__, "dfl.c", "CFG_atom.C")
    )

    prototype: TemplateFun = field(
        default=TemplateFun("prototype", "name", 'int $name(size_t len, char * name, uint32_t id_nr) { {{ placeholder["code"] }} }')
    )

    def check(self):
        # print(self.param, self.label)
        # assert "format" in self.param
        # assert "arg" in self.label
        # assert isinstance(self.label['arg'].type, Array)
        # assert istype_lite(self.label["arg"].type, "Array")
        pass


@with_schema(Block.Schema)
@dataclass
class UdpReceive(Block):

    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>"]})
    )
    
    code: str = field(
        # default=read_template( Path(__file__).with_name("dfl.c"), "UdpReceive.C")
        default=read_template(__name__, "dfl.c", "UdpReceive.C")
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
        # default=read_template(Path(__file__).with_name("dfl.c"), "UdpSend.C")
        default=read_template(__name__, "dfl.c", "UdpSend.C")
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
        # default=read_template( Path(__file__).with_name("dfl.c"), "UdpReceive.C")
        default=read_template(__name__, "dfl.c", "TimerReceive.C")
    )

    def check(self):
        assert "timerrecv" in self.label
        assert "timestamp" in self.label
        
