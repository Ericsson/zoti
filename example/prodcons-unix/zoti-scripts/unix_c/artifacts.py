import networkx as nx

import zoti_graph.genny.core as ty
from zoti_ftn.backend.c import TypeABC
from zoti_ftn.core import Array, Structure, Entry
from zoti_graph import ScriptError

from ports import Timer, Socket
from dumputils import Ref, Default, PolInter, PolUnion


############################
##      GENSPEC PART      ##
############################

def _gen_arg(var, typ, T, casting=False, out=False, **kwargs):
    tt = T.get(typ)
    need_malloc = (isinstance(tt, Array) or isinstance(
        tt, Structure)) and tt.need_malloc()
    if (not casting) and (not out) and (not need_malloc):
        return f"&{var}"
    elif (not casting) and (not out) and need_malloc:
        return f"{var}"
    elif (not casting) and out and (not need_malloc):
        return f"&{var}"
    elif (not casting) and out and need_malloc:
        return f"{var}"
    elif casting and (not out) and (not need_malloc):
        return f"({T.c_name(typ)} *) &{var}"
    elif casting and (not out) and need_malloc:
        return f"({T.c_name(typ)} *) &{var}"
    elif casting and out and (not need_malloc):
        return f"({T.c_name(typ)} *) &{var}"
    elif casting and out and need_malloc:
        return f"({T.c_name(typ)} *) {var}"


def _mangle_c_name(fullname):
    return str(fullname).replace("/", "_").replace("-", "_").replace(".", "_")


def _make_global_inits(name, atoms, ports, G, T):
    port_entries = [G.entry(p) for p in ports]
    inst = {
        "placeholder": None,
        "block": Ref("InitGlobalVariables"),
        "directive": ["pass"],
    }
    code = "".join([
        f"{prefix}{p['usage']}{suffix};\n"
        for p, prefix, suffix in atoms
    ]) + "\n".join([
        T.gen_decl(p.name, p.data_type, static=("probe_buffer" in p.mark))
        for p in port_entries
    ])
    comp = {
        "name": "InitGlobalVariables",
        "prototype": "{{ placeholder['code'] }}",
        "code": code,
    }
    return inst, comp


def _make_init_stage1(name, ports, T):
    inst = {
        "placeholder": "INIT_stage1",
        "block": Ref(f"DFLF_{name}_INIT_stage1"),
        "usage": "{{name}}();"
    }
    code = ""  # TODO: make timer initialization code
    comp = {
        "name": f"DFLF_{name}_INIT_stage1",
        "prototype": 'void {{name}}() { {{ placeholder.code }} }',
        "code": code,
    }
    return inst, comp


def _make_init_stage2(name, probes, timers, G, T):
    inst = {
        "placeholder": "INIT_stage2",
        "block": Ref(f"DFLF_{name}_INIT_stage2"),
        "usage": "{{name}}();",
    }
    # TODO: make proper assignment based on FTN macros
    code = "\n".join(
        [f"{p.name}.name = DFL_atom_table[{p.name}.name & DFL_ATOM_MASK].id_nr;\n"
         for p in probes] +
        [f"dfl_evt_add_timer({p.period}LL, DFLF_{name}_{p.name});\n"
         for p in timers]
    )

    comp = {
        "name": f"DFLF_{name}_INIT_stage2",
        "prototype": 'void {{name}}() { {{ placeholder.code }} }',
        "code": code,
    }
    if timers:
        comp["instance"] = [
            {"placeholder": None, "block": Ref(f"DFLF_{name}_{p.name}")}
            for p in timers
        ]
    return inst, comp


def _make_cfg_iport(name, ports, T):
    inst = {
        "placeholder": None,
        "block": Ref(f"DFLF_{name}_CFG_inport"),
    }
    comp = {
        "name": f"DFLF_{name}_CFG_inport",
        "type": {"module": "Generic.Dfl", "name": "CfgInport"},
        "param": {
            "iports": [{"name": p, "handler": f"DFLF_{name}_{p}"} for p in ports],
        },
        "instance": [
            {"placeholder": None, "block": Ref(f"DFLF_{name}_{p}")} for p in ports],
    }
    return inst, comp


def _make_cfg_oport(name, ports, T):
    inst = {
        "placeholder": None,
        "block": Ref(f"DFLF_{name}_CFG_outport"),
        "directive": ["pass"],
        "bind": [
            {"label_to_label": {"parent": str(glb), "child": str(loc)}}
            for loc, glb in ports
        ],
    }
    comp = {
        "name": f"DFLF_{name}_CFG_outport",
        "type": {"module": "Generic.Dfl", "name": "CfgOutport"},
        "param": {
            "oports": [{"name": loc.name(), "socket": str(loc)}
                       for loc, glb in ports],
        },
    }
    return inst, comp


def _make_cfg_atom(name, ports, init_table, T):

    inst = {
        "placeholder": None,
        "block": Ref(f"DFLF_{name}_CFG_atom"),
        "directive": ["pass"],
        "bind": [{"label_to_label": {"parent": p["name"], "child": p["name"]}}
                 for p in ports],
    }
    comp = {
        "name": f"DFLF_{name}_CFG_atom",
        "type": {"module": "Generic.Dfl", "name": "CfgAtom"},
        "param": {"init_table": init_table}
    }
    return inst, comp


def _make_kernel_component(node, parent, G, T):
    def _is_local(p): return "global_var" not in p.mark

    entry = G.entry(node)
    globs = G.ports(node, select=lambda p: not _is_local(p))
    iports = G.ports(node, select=lambda p: _is_local(p)
                     and p.kind == ty.Dir.IN)
    oports = G.ports(node, select=lambda p: _is_local(p)
                     and p.kind == ty.Dir.OUT)

    # TODO: casting should happen as part of type handling (i.e. by FTN)
    portinfo = [{
        "locid": p.name(),
        "access": T.gen_access_dict(G.entry(p).data_type, read_only=True),
        "prefix": "*",
        "prtarg": f"const {T.c_name(G.entry(p).data_type)}* {G.entry(p).name}",
        "usearg": _gen_arg(
            f"{{{{ label.{p.name()}.name }}}}",
            G.entry(p).data_type, T,
            casting=(any([G.entry(i).kind == ty.Dir.IN
                          for i in G.connected_ports(p)
                          if G.parent(i) == parent])))
    } for p in iports]
    portinfo += [{
        "locid": p.name(),
        "access": T.gen_access_dict(G.entry(p).data_type, read_only=False),
        "prefix": "*",
        "prtarg": f"{T.c_name(G.entry(p).data_type)}* {G.entry(p).name}",
        "usearg": _gen_arg(
            f"{{{{ label.{p.name()}.name }}}}",
            G.entry(p).data_type, T, out=True)
    } for p in oports]

    inst = {
        "placeholder": str(node),
        "block": Ref(_mangle_c_name(node)),
        "bind": (
            [{"label_to_label": {
                "child": p.name(),
                "parent": [o.name() for o in G.connected_ports(p) if G.parent(o) == parent][0], }
              }
             for p in iports + oports] +
            [{"usage_to_label": {"child": p.name(), "usage": G.entry(p).name}}
             for p in globs]
        ),
    }
    if "inline" in entry.mark:
        inst["directive"] = ["expand"]
    else:
        inst["usage"] = ('{{name}}' + f'({", ".join([p["usearg"] for p in portinfo])});')
        
    comp = {
        "name": _mangle_c_name(node),
        "param": entry.parameters,
        "label": ([{"name": p["locid"],
                    "glue": p["access"] | {"prefix": p["prefix"]}}
                   for p in portinfo] +
                  [{"name": p.name(),
                    "usage": G.entry(p).name,
                    "glue": T.gen_access_dict(G.entry(p).data_type, read_only=False)}
                   for p in globs]
                  ),
        "prototype": ('inline static void {{name}} ('
                      + ", ".join([p["prtarg"] for p in portinfo])
                      + ') { {{ placeholder.code }} }'),
        "code": entry.extern,
        "_info": entry._info
    }
    return inst, comp


def _make_actor_scenario(node, G, T):
    # for all actors make ExecuteAndSend code
    prefix = _mangle_c_name(str(node))
    entry = G.entry(node)
    out_ports = G.ports(node, select=lambda n: n.kind == ty.Dir.OUT and "inter_var" not in n.mark)
    inter_ports = G.ports(node, select=lambda n: "inter_var" in n.mark)

    snd_specs = [G.entry(p).sender_genspec(prefix, T) for p in out_ports]
    sched = [
        n for n in list(nx.dfs_preorder_nodes(G.node_projection(node)))
        if not isinstance(G.entry(n), ty.Port)
    ]
    binds = [
        {"child": G.entry(p_child).name, "parent": G.entry(p_parent).name}
        for p_child in G.ports(node)
        for p_parent in G.connected_ports(p_child)
        if G.parent(p_parent) == G.parent(node)
    ]
    
    ############

    def _nameAndTy(p):
        return (f"{{{{label.{G.entry(p).name}.name}}}}", G.entry(p).data_type)

    usage =  [
        T.get(ty).gen_ctor(var, f"(*{var})")
        for p in out_ports
        for var, ty in (_nameAndTy(p),)
    ] + [
        T.gen_decl(f"*{var}", ty)
        for p in inter_ports
        for var, ty in (_nameAndTy(p),)
    ] + [
        T.get(ty).gen_ctor(var, f"(*{var})")
        for p in inter_ports
        for var, ty in (_nameAndTy(p),)
    ] + [
        '{{ placeholder.code }}'
    ] + [
        T.get(ty).gen_desctor(var, ty.value)
        for p in inter_ports
        for var, ty in (_nameAndTy(p),)
    ] + [
        T.get(ty).gen_desctor(var, ty.value)
        for p in out_ports
        for var, ty in (_nameAndTy(p),)
    ]
    inst = {
        "placeholder": entry.name,
        "block": Ref(prefix),
        "directive": ["expand"],  # TODO
        "bind": [{"label_to_label": bind} for bind in binds],
        "usage": "\n".join(usage),
        "_info": entry._info,
    }

    kerns = [
        _make_kernel_component(n, node, G, T)
        for n in sched
        if isinstance(G.entry(n), ty.KernelNode)
    ]

    cp_insts = [
        inst
        for inst, _ in kerns
    ] + [
        inst
        for snd_insts, _ in snd_specs
        for inst in snd_insts
    ]

    comp = {
        "name": prefix,
        "type": {"module": "Generic", "name": "Composite"},
        "label": [{"name": G.entry(p).name} for p in inter_ports],
        "param": {"schedule": [inst["placeholder"] for inst in cp_insts]},
        "instance": cp_insts,
        "_info": entry._info,
    }
    return inst, (
        [comp]
        + [cp for _, cp in kerns]
        + [cp for _, snd_blocks in snd_specs for cp in snd_blocks]
    )


def _make_iport_reaction(pltf_name, actor_id, port_id, G, T):
    iport = G.entry(port_id)
    oports = [G.entry(p) for p in G.ports(actor_id, select=lambda p: p.kind == ty.Dir.OUT)]
    rcv_labels, rcv_proto, rcv_insts, rcv_blocks = iport.receiver_genspec(pltf_name, T)
    port_scenarios = [y for x, y in G.node_projection(actor_id).out_edges(port_id)
                      if G.entry(y).mark.get("scenario")]
    assert port_scenarios
    #############

    # TODO: ports between scenarios
    ports = (rcv_labels +
             [{"name": p.name} for p in oports] +
             [{"name": G.entry(p).name, "usage": G.get_mark("buff_name", p)}
              for p in G.ports(actor_id, select=lambda p: p.kind == ty.Dir.IN)
              if p != port_id])

    oport_name_type = [
       (f"{'* ' if T.get(p.data_type).need_malloc() else ''}{{{{label.{p.name}.name}}}}",
        p.data_type) for p in oports]
    proto = (
        rcv_proto
        + "\n ".join([T.gen_decl(name, ty) for name, ty in oport_name_type])
        + '\n {{ placeholder.code }}\n}')

    # TODO:
    preproc = None

    # TODO:
    detector = None

    scens = [_make_actor_scenario(scen, G, T) for scen in port_scenarios]
    # unique_blocks = {blk["name"]: blk for _, blks in scens for blk in blks}

    insts = (rcv_insts
             + ([preproc] if preproc else [])
             + ([detector] if detector else [])
             + [scen_inst for scen_inst, _ in scens])

    schedule = [inst.get("placeholder") for inst in insts]

    comp = {
        "name": f"DFLF_{pltf_name}_{iport.name}",
        "type": {"module": "Generic", "name": "Composite"},
        "param": {"schedule": schedule},
        "label": ports,
        "prototype": proto,
        "instance": insts,
        "_info": iport._info,
    }
    return [comp] + rcv_blocks + [blk for _, blks in scens for blk in blks]


def genspec(G, T, prepare_platform_ports, expand_actors, fuse_actors,
            prepare_intermediate_ports, typedefs, **kwargs):
    specs = {}

    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        name = pltf.name()
        glbs = G.ports(pltf, select=lambda p: "global_var" in p.mark)
        probes = [
            G.entry(p)
            for p in G.ports(pltf, select=lambda p: "probe_buffer" in p.mark)]
        timers = [
            G.entry(p)
            for p in G.ports(pltf, select=lambda p: isinstance(p, Timer))]
        atomports = [
            ({"name": "atom_table_len", "usage": "DFL_dyn_atom_table_len"},
             "static size_t ", " = 0"),
            ({"name": "atom_table_inited", "usage": "DFL_atom_table_inited"},
             "static bool ", " = false"),
            ({"name": "atom_table", "usage": "DFL_atom_table"},
             "static DFL_atom_entry_t ", "[] = {\n" +
             "".join([
                 f"{{\"{p.mark['probe_buffer']}\", DFL_ATOM_INVALID_BIT}}\n"
                 for p in probes
             ]) + "}")]
        if "init_atom_table" in G.entry(pltf).mark:
            atomports += [
                ({"name": "dyn_table", "usage": "DFL_dyn_atom_table"},
                 "DFL_atom_entry_t *", " = 0"),
                ({"name": "dyn_table_inited", "usage": "DFL_dyn_atom_table_inited"},
                 "static bool ", " = false"),
            ]

        glbs_inst, glbs_comp = _make_global_inits(name, atomports, glbs, G, T)

        stg1_inst, stg1_comp = _make_init_stage1(name, [], T)

        stg2_inst, stg2_comp = _make_init_stage2(name, probes, timers, G, T)

        iport = [
            G.entry(p).name
            for src in G.ports(pltf, select=lambda p: p.kind == ty.Dir.IN
                               and isinstance(p, Socket))
            for p in G.connected_ports(src)
            if G.parent(p) and G.parent(G.parent(p)) and G.parent(G.parent(p)) == pltf
        ]
        icfg_inst, icfg_comp = _make_cfg_iport(name, iport, T)

        oport = [
            (p, G.entry(G.entry(p).mark["socket_port"]).name)
            # (p, G.entry(p).name)
            for p in G.ports(pltf, select=lambda p: p.kind == ty.Dir.OUT)
            # for p in G.ports(pltf, select=lambda p: p.mark.get("socket"))
        ]
        ocfg_inst, ocfg_comp = _make_cfg_oport(name, oport, T)

        acfg_inst, acfg_comp = _make_cfg_atom(
            name,
            [a for a, _, _ in atomports],
            "init_atom_table" in G.entry(pltf).mark, T)

        cfg_names = {"atom": acfg_comp["name"],
                     "inport": icfg_comp["name"],
                     "outport": ocfg_comp["name"]}

        main = {
            "name": "Main",
            "type": {"module": "Generic.Dfl", "name": "Main"},
            "requirement": {
                "include": T.requirements() + ["<stdio.h>"]
                + ['"DFL_core.h"', '"DFL_util.h"', '"dfl_cfg.h"', '"dfl_evt.h"']
                + [f'"{h}"' for h in typedefs.keys()]
            },
            "label": [a for a, _, _ in atomports] + [{"name": p} for _, p in oport],
            "param": {"CFG": cfg_names},
            "prototype": 'int main(int argc, char * argv[]) { {{placeholder.code}} }',
            "instance": [
                glbs_inst,
                stg1_inst,
                stg2_inst,
                icfg_inst,
                ocfg_inst,
                acfg_inst,
            ],
        }

        child_cps = []
        for actor in G.children(pltf, select=lambda n: isinstance(n, ty.ActorNode)):
            for port in G.ports(actor, select=lambda p: p.kind == ty.Dir.IN):
                child_cps.extend(_make_iport_reaction(name, actor, port, G, T))
        unique_child_cps = {cp["name"]: cp for cp in child_cps}
        cps = [main, glbs_comp, stg1_comp, stg2_comp, icfg_comp, ocfg_comp,
               acfg_comp] + list(unique_child_cps.values())

        preamble = {
            "module": name,
            "top": "Main",
        }

        defaults = PolInter([{
            "label": [{"usage":  PolUnion("{{label[p].name}}")}],
            "instance": [{
                "bind": [{
                    "label_to_label": {
                        "usage": PolUnion("{{label[p].name}}")}}]
            },]
        },])

        specs[pltf.name()] = [preamble, Default(
            [{"block": defaults}, {"block": cps}])]

    return specs


#############################
##      TYPEDEFS PART      ##
#############################

def typedefs(G, T, port_inference, **kwargs):
    types = dict()
    for port in [p for p in G.ir.nodes if isinstance(G.entry(p), ty.Port)]:
        entry = G.entry(port).data_type
        if entry.uid.module == "__local__":
            continue
        if entry not in types:
            types[entry] = []
        types[entry].append(port)

    deps = nx.DiGraph()
    root_dep = Entry("__root__")
    deps.add_node(root_dep)
    for typ, ports in types.items():
        try:
            for typdep in [Entry(t.ref) for t in T.get(typ).select_types(of_class="ref")]:
                deps.add_edge(typ, typdep)
            deps.add_edge(root_dep, typ)
        except Exception as e:
            msg = f"Cannot load type '{typ.uid}' needed for {ports}:\n{e}"
            raise ScriptError(msg, G.entry(ports[0]))
    tydefs = ""
    # print(deps.edges)
    # print(list(nx.dfs_postorder_nodes(deps)))
    for typ in list(nx.dfs_postorder_nodes(deps))[:-1]:
        tydefs += T.gen_c_typedef(typ) + "\n"
        tydefs += "".join(T.gen_access_macros(typ)) + "\n"
    return {"types.h": tydefs}


############################
##      GENDEPL PART      ##
############################

_port_name_LUT = {}


def _port_spec(G, uid):
    entry = G.entry(uid)
    if entry.kind == ty.Dir.IN:
        socket_name = entry.name
    else:
        socket_name = G.entry(entry.mark["socket_port"]).name
    _port_name_LUT[uid] = entry.name
    port_dir = "InputNode" if entry.kind == ty.Dir.IN else "OutputNode"
    if entry.kind == ty.Dir.IN:
        port_intrinsic = {
            "name": "InputNode",
            "description": "Declaration of InputNode",
            "roles": ["intrinsic", "end-point", "input"],
            "parameters": [
                "data-type", "flow-name", "abstract",
                "DFL-sys-trig-source", "DFL-INTR-node-slice"
            ],
        }
    else:
        port_intrinsic = {
            "name": "OutputNode",
            "description": "Declaration of OutputNode",
            "roles": ["intrinsic", "end-point", "output"],
            "expansion": ["IdentityNode", {"data": "in", "": "out"}],
            "parameters": ["data-type", "abstract"],
        }
    return [
        entry.name,
        port_dir,
        {
            "node-name": socket_name
        },
        port_intrinsic
    ]


def _atom_spec(G, uid):
    entry = G.entry(uid)
    port_intrinsic = {
        "name": "TrigCounter2",
        "description": [],
        "roles": ["intrinsic", "counter"],
        "atoms": ["{counter-name}"],
        "parameters": ["data-type", "data-type-anchor", "counter-name"],
    }

    return [
        entry.mark["probe_buffer"],
        "TrigCounter2",
        {
            "data-type-anchor": "Common.Timestamp",
            "data-type": "Monitor.Counter64",
            "counter-name": entry.mark["probe_buffer"],
            "DFL-proposed-port": "trig",
            "node-name": entry.mark["probe_buffer"]
        },
        port_intrinsic
    ]


def gendepl(G, **kwargs):
    depl = {}
    root_entry = G.entry(G.root)
    depl["name"] = f"{root_entry.name}-depl"
    depl["description"] = root_entry._info.get("description")
    depl["parameters"] = ["trig-port"]
    depl["nodes"] = []
    depl["edges"] = []

    cfg_port = 0xdf0
    for idx, pltf in enumerate(G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode))):
        entry = G.entry(pltf)
        cfg_port += 1
        node = [
            f"proc-{entry.name}",
            # f"proc-{idx}-{entry.name}",
            entry.name,
            {
                "node-name": f"proc-{entry.name}",
                "deployment-host": "localhost",
                "deployment-bin-file": f"{entry.name}.bin",
                "deployment-cfg-port": str(hex(cfg_port)),
                "deployment-in-window": idx+1,
            },
            {
                "name": f"proc-{entry.name}",
                # "name": f"proc-{idx}-{entry.name}",
                "nodes": [
                    _port_spec(G, p)
                    for p in G.ports(pltf, select=lambda x: x.kind != ty.Dir.SIDE)
                ] + [
                    _atom_spec(G, p)
                    for p in G.ports(pltf, select=lambda x: "probe_buffer" in x.mark)
                ]
            }

        ]

        depl["nodes"].append(node)

    # idx = 0
    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        entry = G.entry(pltf)
        # idx += 1
        for src, dst in G.node_edges(pltf, which="in+outside"):
            src_entry = G.entry(src)
            dst_entry = G.entry(dst)
            if isinstance(src_entry, ty.BasicNode) and src_entry.type == "SYSTEM":
                depl["edges"].append([
                    "SYSTEM",
                    f"proc-{entry.name}:{dst_entry.name}",
                    # f"proc-{idx}-{entry.name}:{dst_entry.name}",
                    dst_entry.to_json()
                ])
            else:
                srcn_entry = G.entry(G.parent(src))
                depl["edges"].append([
                    f"proc-{srcn_entry.name}:{_port_name_LUT[src]}",
                    f"proc-{entry.name}:{dst_entry.name}",
                    dst_entry.to_json()
                ])

    return depl
