from copy import deepcopy
from typing import Any

from zoti_graph import ScriptError, ContextError
from dumputils import Ref
import zoti_graph.genny as ty


def _mangle_c_name(fullname):
    return str(fullname).replace("/", "_").replace("-", "_").replace(".", "_").replace("^", "__")



def merge_attrs(plist, key, err_msg=""):
    """Utility which returns the merged attributes from a list of objects.

    :param plist: list of objects containing member *key*
    :param key: member holding the dictionary of attributes
    *err_msg*: The error message printed in case the attributes cannot be merged
    """
    assert hasattr(plist[0], key)
    ref = deepcopy(getattr(plist[0], key))
    for this in plist[1:]:
        assert hasattr(this, key)
        for k, v in getattr(this, key).items():
            if k in ref:
                if ref.get(k) != v:
                    err_msg += f"{k}:{v} and {k}:{ref.get(k)}"
                    raise ContextError(err_msg, obj=this, context_obj=plist[0])
            else:
                ref[k] = v
    return ref


def make_port_type(port_type_attrs, orig_port):
    if not port_type_attrs:
        return Assign(**vars(orig_port))
    assert "type" in port_type_attrs
    ptype = port_type_attrs["type"]
    if ptype == "UDP-socket":
        return Socket(**port_type_attrs, **vars(orig_port))
    elif ptype == "timer":
        return Timer(**port_type_attrs, **vars(orig_port))
    elif ptype == "assign":
        return Assign(**vars(orig_port))
    else:
        raise ValueError(f"Unknown port type '{ptype}'")
    

######## PORT TYPES ########

class PortType(ty.Port):
    
    def __init__(self, **kwargs):
        super(PortType, self).__init__(**kwargs)

    def make_data_type(self, T, data_type_attrs):
        try:
            self.data_type=T.make_entry(**data_type_attrs)
        except Exception as e:
            msg = f"Cannot deduce data type: {e}"
            raise ScriptError(msg, obj=self)
        
    def make_markings(self, markings):
        self.mark = markings

    def update_input_buffer_type(self, T):
        raise ContextError(f"{type(self)} cannot be platform input", obj=self)
        
    def new_output_socket_port(self, T):
        raise ContextError(f"{type(self)} cannot be platform output", obj=self)

    def receiver_genspec(self, T):
        raise ContextError(f"{type(self)} cannot be platform input", obj=self)
        
    def sender_genspec(self, T):
        raise ContextError(f"{type(self)} cannot be platform output", obj=self)

    
class Assign(PortType):
    def __init__(self, **kwargs):
        super(Assign, self).__init__(**kwargs)


class Socket(PortType):
    ext_name: str

    def __init__(self, external_name: str = None, **kwargs):
        super(Socket, self).__init__(**kwargs)
        self.ext_name = external_name

    def update_input_buffer_type(self, T):
        self.data_type = T.make_entry(name="DflSys.UdpPacket")

    def new_output_socket_port(self, socket_id, T):
        self.mark["socket_port"] = socket_id
        self.mark["socket_name"] = socket_id.name()
        return Assign(
            name=socket_id.name(),
            data_type=T.make_entry(from_ftn="integer(range: -1..0xFFFFFF)", value="0"),
            mark={"global_var": True, "socket": True},
            kind=ty.Dir.SIDE,
            _info=self._info
        )
        
    def receiver_genspec(self, prefix: str, T):
        exp_type, exp_type_name = (T.get(self.data_type), T.c_name(self.data_type))
        exp_base_size = exp_type._gen_base_size_expr(exp_type_name)
        exp_size = exp_type.gen_size_expr(exp_type_name)
        buf_type = T.make_entry(name="DflSys.UdpPacket")
        var = f"(({exp_type_name} *)&{{{{label.{self.name}.name}}}})"

        labels = [
            {"name": "socket", "usage": "DFL_socket"},
            {"name": "size"},
            {"name": self.name, "usage": f"udp2ram_{self.name}"},
        ]
        # prototype expects to be closed by caller
        proto = (" void {{name}}(int {{label.socket.name}}) {" +
                 "\n uint16_t {{label.size.name}};" +
                 "\n" + T.gen_decl(f"{{{{label.{self.name}.name}}}}", buf_type) +
                 "\n"
                 )
        instances = [{
            "placeholder": "receive",
            "block": Ref(f"recv_{prefix}_{self.name}"),
            "directive": ["expand"],
            "bind": [
                {"label_to_label": {"parent": self.name, "child": "ram"}},
                {"label_to_label": {"parent": "socket", "child": "socket"}},
                {"label_to_label": {"parent": "size", "child": "size"}},
                {"value_to_param": {"child": "expected_type", "value": exp_type_name}},
                {"value_to_param": {"child": "expected_base_size",  "value": exp_base_size}},
                {"value_to_param": {"child": "expected_size", "value": exp_size}}
            ]
        }, {
            "placeholder": "marshal",
            "block": Ref(f"marshal_{prefix}_{self.name}"),
            "directive": ["expand"],
            "bind": [
                {"label_to_label": {"parent": self.name, "child": self.name}},
            ]

        }]
        # print(T.get(exp_type).gen_unmarshal(var, f"(*{var})"))
        blocks = [{
            "name": f"recv_{prefix}_{self.name}",
            "type": {"module": "Generic.Dfl", "name": "UdpReceive"}
        }, {
            "name": f"marshal_{prefix}_{self.name}",
            "code": T.get(exp_type).gen_unmarshal(var, f"(*{var})"),
            "prototype": '{{ placeholder["code"] }}'
        }]
        return labels, proto, instances, blocks

    def sender_genspec(self, prefix, T):
        exp_type, exp_type_name = (T.get(self.data_type), T.c_name(self.data_type))
        exp_size = exp_type.gen_size_expr(exp_type_name)
        var = f"{{{{label.{self.name}.name}}}}"
        bname = f"{prefix}_{self.name}"
        
        instances = [{                                       # marshalling first
            "placeholder": f"marshal_{bname}",
            "block": None,
            "directive": ["expand"],
            "usage": exp_type.gen_marshal(var, f"(*{var})"),
            "bind": [{"label_to_label": {"child": self.name, "parent": self.name}}]
        }, {                                                 # send after marshalling
            "placeholder": f"send_{bname}",
            "block": Ref(f"send_{bname}"),
            "directive": ["expand"],
            "bind": [
                {"value_to_param": {"child": "expected_size", "value": exp_size}},
                {"label_to_label": {
                    "child": "data", "parent": self.name,
                    "usage": ("" if exp_type.need_malloc() else "&") + '{{label[p].name}}'}},
                {"usage_to_label": {"child": "socket",
                                    "usage": self.mark["socket_name"]}},
                {"usage_to_label": {"child": "size",
                                    "usage": f"{self.name}_size"}},

            ]
        }]

        blocks = [{
            "name": f"send_{bname}",
            "type": {"module": "Generic.Dfl", "name": "UdpSend"}
        }]
        return instances, blocks

    def to_json(self):
        jsn = {
            "trigger-type": "socket",
            "transport-type": "UDP"
        }
        if self.ext_name:
            jsn["external-name"] = self.ext_name
        return jsn


class Timer(PortType):
    period: int

    def __init__(self, period: int, **kwargs):
        super(Timer, self).__init__(**kwargs)
        self.period = period
        
    def update_input_buffer_type(self, T):
        self.data_type = T.make_entry(name="Common.Timespec")
    
    def receiver_genspec(self, prefix: str,  T):
        buf_type = T.make_entry(name="Common.Timespec")
        labels = [
            {"name": "timestamp", "usage": "DFL_timestamp"},
            {"name": self.name, "usage": f"timerrecv_{self.name}",
             "glue": T.gen_access_dict(buf_type, read_only=False)},
        ]
        # prototype expects to be closed by caller
        proto = (" void {{name}}(int64_t {{label.timestamp.name}}) {" +
                 "\n" + T.gen_decl(f"{{{{label.{self.name}.name}}}}", buf_type) +
                 "\n"
                 )
        instances = [{
            "placeholder": "read_timer",
            "block": Ref(f"read_timer_{prefix}_{self.name}"),
            "directive": ["expand"],
            "bind": [
                {"value_to_param": {"child": "period",
                                    "value": str(self.period)}},
                {"value_to_param": {"child": "callback",
                                    "value": f"DFLF_{prefix}_{self.name}"}},
                {"label_to_label": {"parent": "timestamp", "child": "timestamp"}},
                {"label_to_label": {"parent": self.name, "child": "timerrecv"}},
            ],
        }]
        blocks = [{
            "name": f"read_timer_{prefix}_{self.name}",
            "type": {"module": "Generic.Dfl", "name": "TimerReceive"}
        }]
        return labels, proto, instances, blocks

    def to_json(self):
        return {
            "trigger-type": "timer",
            "period": self.period
        }
