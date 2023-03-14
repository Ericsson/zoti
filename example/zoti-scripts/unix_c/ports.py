from copy import deepcopy

from zoti_tran import ScriptError, ContextError
from dumputils import Ref


def _mangle_c_name(fullname):
    return str(fullname).replace("/", "_").replace("-", "_").replace(".", "_").replace("^", "__")


######## PORT TYPES ########

class PortTypeABC:
    pass


class Assign(PortTypeABC):
    pass


class Socket(PortTypeABC):
    def buffer_type(self):
        return {"name": "DflSys.UdpPacket"}

    def receiver_genspec(self, iport_name: str, prefix: str,  T):
        labels = [
            {"name": "socket", "usage": ["DFL_socket"]},
            {"name": "size"},
            {"name": iport_name, "usage": [f"udp2ram_{iport_name}"]},
        ]
        # prototype expects to be closed by caller
        proto = ["name",
                 " void $name(int {{label.socket.name}}) {\n"
                 " uint16_t {{label.size.name}};\n"  # +
                 # T.gen_decl(f"{{{{label.{iport_name}.name}}}}", "DflSys.UdpPacket") + "\n"
                 ]
        instances = [{
            "placeholder": "receive",
            "block": Ref(f"recv_{prefix}_{iport_name}"),
            "directive": ["expand"],
            "bind": [
                {"label_to_label": {"parent": iport_name, "child": "ram"}},
                {"label_to_label": {"parent": "socket", "child": "socket"}},
                {"label_to_label": {"parent": "size", "child": "size"}},
            ],
        }]
        blocks = [{
            "name": f"recv_{prefix}_{iport_name}",
            "type": {"module": "Generic.Dfl", "name": "UdpReceive"}
        }]
        return labels, proto, instances, blocks

    def sender_genspec(self, oport_id, oport_entry, connected_name,  T):
        var = f"{{{{label.{oport_entry.name}.name}}}}"
        oport_ty = oport_entry.data_type
        oport_tyspec = T.get(oport_ty["type"])
        oport_name = oport_entry.name

        labels = []

        usage = [
            oport_tyspec.gen_ctor(var, f"(*{var})"),
            T.gen_decl(var, **oport_ty),
            oport_tyspec.gen_marshal(var, f"(*{var})"),
            oport_tyspec.gen_desctor(var, oport_ty.get("value"))
        ]

        instances = [{                                       # marshalling first
            "placeholder": f"marshal_{oport_id}",
            "block": None,
            "directive": ["expand"],
            "usage": [oport_tyspec.gen_marshal(var, f"(*{var})")],
            "bind": [{"label_to_label": {"child": oport_name, "parent": oport_name}}]
        }, {                                                 # send after marshalling
            "placeholder": f"send_{oport_id}",
            "block": Ref(f"send_{_mangle_c_name(repr(oport_id))}"),
            "directive": ["expand"],
            "bind": [
                {"label_to_label": {"child": "data", "parent": oport_name}},
                {"usage_to_label": {"child": "socket",
                                    "usage": [connected_name]}},

            ]
        }]

        blocks = [{
            "name": f"send_{_mangle_c_name(repr(oport_id))}",
            "type": {"module": "Generic.Dfl", "name": "UdpSend"}
        }]
        return labels, usage, instances, blocks


class Timer(PortTypeABC):
    period: int

    def __init__(self, period: int):
        self.period = period

    def buffer_type(self):
        return {"name": "Common.Timespec"}

    def receiver_genspec(self, iport_name: str, prefix: str,  T):
        labels = [
            {"name": "timestamp", "usage": ["DFL_timestamp"]},
            {"name": iport_name, "usage": [f"timerrecv_{iport_name}",],
             "glue": T.gen_access_dict("Common.Timespec", read_only=False)},
        ]
        # prototype expects to be closed by caller
        proto = ["name",
                 " void $name(int64_t {{label.timestamp.name}}) {\n"  # +
                 # T.gen_decl(f"{{{{label.{iport_name}.name}}}}",
                 #            "Common.Timespec") + "\n"
                 ]
        instances = [{
            "placeholder": "read_timer",
            "block": Ref(f"read_timer_{prefix}_{iport_name}"),
            "directive": ["expand"],
            "bind": [
                {"value_to_param": {"child": "period",
                                    "value": str(self.period)}},
                {"value_to_param": {"child": "callback",
                                    "value": f"DFLF_{prefix}_{iport_name}"}},
                {"label_to_label": {"parent": "timestamp", "child": "timestamp"}},
                {"label_to_label": {"parent": iport_name, "child": "timerrecv"}},
            ],
        }]
        blocks = [{
            "name": f"read_timer_{prefix}_{iport_name}",
            "type": {"module": "Generic.Dfl", "name": "TimerReceive"}
        }]
        return labels, proto, instances, blocks

######## SYNC PROCEDURES ########


def _merge_dicts(plist, key, err_msg=""):
    ref = deepcopy(plist[0])
    assert hasattr(ref, key)
    for this in plist[1:]:
        assert hasattr(this, key)
        for k, v in getattr(this, key).items():
            if k in getattr(ref, key):
                if getattr(ref, key).get(k) != v:
                    err_msg += f"{k}:{v} and {k}:{getattr(ref, key).get(k)}"
                    raise ContextError(err_msg, obj=this, context_obj=ref)
            else:
                getattr(ref, key)[k] = v
    return ref


def make_data_type(plist, T, pids=None):
    """Syncs a list of port entries *plist* which are supposed to be
    interconneted and resolves the common data type. *pids* are the
    lit of UIDs of the ports, and can be provided for documenting
    exceptions.

    """
    if len(plist) == 0:
        return
    ref = _merge_dicts(plist, "data_type", "Data type argument mismatch: ")
    try:
        return T.make_type(**ref.data_type)
    except Exception as e:
        msg = f"Cannot deduce data type for ports: {pids}\n{e}"
        raise ScriptError(msg, obj=ref)


def make_port_type(plist, pids=None):
    """Syncs a list of port entries *plist* which are supposed to be
    interconneted and resolves their common port type. *pids* are the
    lit of UIDs of the ports, and can be provided for documenting
    exceptions.

    """
    def _build_port(type, **kwargs):
        if type == "socket":
            return Socket()
        elif type == "timer":
            return Timer(**kwargs)
        elif type == "assign":
            return Assign()
        elif type == "block-buffer":
            return BlockBuffer(**kwargs)
        else:
            raise ValueError(f"Unknown port type '{type}'")

    if len(plist) == 0:
        return
    ref = _merge_dicts(plist, "port_type", "Port type argument mismatch: ")
    if not ref:
        return Assign()
    try:
        return _build_port(**ref.port_type)
    except Exception as e:
        msg = f"Cannot deduce port type for ports: {pids}\n{e}"
        raise ScriptError(msg, obj=ref)


def make_markings(plist, pids=None):
    """Syncs a list of port entries *plist* which are supposed to be
    interconneted and resolves the common markings.

    """
    if len(plist) == 0:
        return
    ref = _merge_dicts(plist, "mark", "Data type argument mismatch: ")
    return ref.mark


############ DROPPED ###############


class BlockBuffer(PortTypeABC):
    def header_funcs(self, port_name,):
        instances = [{
            "placeholder": None,
            "block": Ref(f"{port_name}_alloc"),
            "directive": ["pass"],
        }, {
            "placeholder": None,
            "block": Ref(f"{port_name}_pop"),
            "directive": ["pass"],
        }]
        components = [{
            "name": f"{port_name}_alloc",
            "prototype": ["name", "inline static int16_t $name(Common__StreamId_t id, uint16_t block_max){ {{ placeholder['code'] }} }"],
            "code": f"""
int16_t blk_nr = {port_name}.next[id];
int16_t blk_start = {port_name}.start[id];
if (blk_nr == blk_start)
  return -1;
if (blk_nr+1 >= block_max)
  {port_name}.next[id] = 0;
else
  {port_name}.next[id]++;
if (blk_start < 0)
  {port_name}.start[id] = blk_nr;
return blk_nr;
""",
        }, {
            "name": f"{port_name}_pop",
            "prototype": ["name", "inline static int16_t $name(Common__StreamId_t id, uint16_t block_max){ {{ placeholder['code'] }} }"],
            "code": f"""
int16_t blk_nr = {port_name}.start[id];
if (blk_nr >= 0) {{
  int16_t blk_start = blk_nr + 1;
  if (blk_start >= block_max) {{
    blk_start = 0;
  }}
  if (blk_start == {port_name}.next[id]) {{
    {port_name}.next[id] = 0;
    {port_name}.start[id] = -1;
  }} else {{
    {port_name}.start[id] = blk_start;
  }}
}}
return blk_nr;
"""
        }]

        return instances, components
