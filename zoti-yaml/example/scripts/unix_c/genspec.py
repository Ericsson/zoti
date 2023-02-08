import networkx as nx

from dumputils import Ref, Default, WithCreate
import zoti_graph.core as ty
from zoti_ftn.backend.c import TypeABC
from zoti_ftn.core import Array, Structure
from zoti_tran import ScriptError

from ports import BlockBuffer, Timer, Socket

# from pprint import pprint

def _gen_arg(var, typ, T, casting=False, out=False, **kwargs ):
    tt = T.get(typ)
    match (casting, out, isinstance(tt, Array) or isinstance(tt, Structure)):
        case(False, False, False): # not casting, Input, no Array/struct
            return f"&{var}"
        case(False, False, True):  # not casting, Input, Array/struct
            return f"{var}"
        case(False, True, False):  # not casting, Output, no Array/struct
            return f"&{var}"
        case(False, True, True):   # not casting, Output, Array/struct
            return f"{var}"
        case(True, False, False):  # casting, Input, no Array/struct
            return f"({T.c_name(typ)} *) &{var}"
        case(True, False, True):   # casting, Input, Array/struct
            return f"({T.c_name(typ)} *) &{var}"
        case(True, True, False):   # casting, Output, no Array/struct
            return f"({T.c_name(typ)} *) &{var}"
        case(True, True, True):    # casting, Output, Array/struct
            return f"({T.c_name(typ)} *) {var}"

    # if not out:
    #     if isinstance(tt, Array) or isinstance(tt, Structure):
    #         return f"({self.c_name(typ)} *) &{var}"
    #     else:
    #         return f"({self.c_name(typ)}) {var}"
    # else:
    #     if isinstance(tt, Array) or isinstance(tt, Structure):
    #         return var
    #     else:
    #         return f"&{var}"
        

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
        f"{prefix}{p['usage'][0]}{suffix};\n"
        for p, prefix, suffix in atoms
    ]) + "\n".join([
        T.gen_decl(p.name, **p.data_type, static="probe_buffer" in p.mark)
        for p in port_entries
    ])
    comp = {
        "name": "InitGlobalVariables",
        "prototype": ["{{ placeholder['code'] }}"],
        "code": code,
    }
    return inst, comp


def _make_init_stage1(name, ports, T):
    inst = {
        "placeholder": "INIT_stage1",
        "block": Ref(f"DFLF_{name}_INIT_stage1"),
        "usage": ["name", "$name();"],
    }
    code = ""  # TODO: make timer initialization code
    comp = {
        "name": f"DFLF_{name}_INIT_stage1",
        "prototype": ["name", 'void $name() { {{ placeholder.code }} }'],
        "code": code,
    }
    return inst, comp


def _make_init_stage2(name, probes, timers, G, T):
    inst = {
        "placeholder": "INIT_stage2",
        "block": Ref(f"DFLF_{name}_INIT_stage2"),
        "usage": ["name", "$name();"],
    }
    # TODO: make proper assignment based on FTN macros
    code = "\n".join(
        [f"{p.name}.name = DFL_atom_table[{p.name}.name & DFL_ATOM_MASK].id_nr;\n"
         for p in probes] +
        [f"dfl_evt_add_timer({p.port_type.period}LL, DFLF_{name}_{p.name});\n"
         for p in timers]
    )
    
    comp = {
        "name": f"DFLF_{name}_INIT_stage2",
        "prototype": ["name", 'void $name() { {{ placeholder.code }} }'],
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
    iports = G.ports(node, select=lambda p: _is_local(p) and p.dir == ty.Dir.IN)
    oports = G.ports(node, select=lambda p: _is_local(p) and p.dir == ty.Dir.OUT)

    # TODO: casting should happen as part of type handling (i.e. by FTN)
    portinfo = [{
        "locid": p.name(),
        "access": T.gen_access_dict(G.entry(p).data_type["type"], read_only=True),
        "prefix": "*",
        "prtarg": f"const {T.c_name(G.entry(p).data_type['type'])}* {G.entry(p).name}",
        "usearg": _gen_arg(
            f"{{{{ label.${p.name()}.name }}}}", G.entry(p).data_type['type'], T,
            casting=(any([G.entry(i).dir==ty.Dir.IN
                          for i in G.connected_ports(p)
                          if G.parent(i) == parent])))
    } for p in iports]
    portinfo += [{
        "locid": p.name(),
        "access": T.gen_access_dict(G.entry(p).data_type["type"], read_only=False),
        "prefix": "*",
        "prtarg": f"{T.c_name(G.entry(p).data_type['type'])}* {G.entry(p).name}",
        "usearg": _gen_arg(f"{{{{ label.${p.name()}.name }}}}",
                           G.entry(p).data_type['type'], T, out=True)
    } for p in oports]
    
    # print("¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤")
    # print(iports + oports)
    # print([[o.name() for o in G.connected_ports(p) if G.parent(o) == parent] for p in iports + oports])
    inst = {
        "placeholder": str(node),
        "block": Ref(_mangle_c_name(node)),
        "bind": (
            [{"label_to_label": {
                "child": p.name(),
                "parent": [
                    o.name() for o in G.connected_ports(p) if G.parent(o) == parent][0],}
              } for p in iports + oports] +
            [{"usage_to_label": {"child": p.name(), "usage": [G.entry(p).name]}}
             for p in globs]
        ),
    }
    if "inline" in entry.mark:
        inst["directive"] = ["expand"]
    else:
        inst["usage"] = (["name"] + [p.name() for p in iports + oports] +
                         [f'$name({", ".join([p["usearg"] for p in portinfo])});'])
    comp = {
        "name": _mangle_c_name(node),
        "param": entry.parameters,
        "label": ([{"name": p["locid"],
                    "glue": p["access"] | {"prefix": p["prefix"]}}
                   for p in portinfo] +
                  [{"name": p.name(), "usage": [G.entry(p).name],
                    "glue": T.gen_access_dict(
                        G.entry(p).data_type["type"], read_only=False)}
                   for p in globs]
                  ),
        "prototype": [
            "name",
            (f'inline static void $name ({", ".join([p["prtarg"] for p in portinfo])}) '
             '{ {{ placeholder.code }} }')], 
        "code": entry.extern,
        "_info": entry._info
    }
    return inst, comp


def _make_actor_scenario(node, G, T):
    # for all actors make ExecuteAndSend code
    entry = G.entry(node)
    binds = [
        {"child": G.entry(p_child).name, "parent": G.entry(p_parent).name}
        for p_child in G.ports(node)
        for p_parent in G.connected_ports(p_child)
        if G.parent(p_parent) == G.parent(node)
    ]
    inter_ports = G.ports(node, select=lambda n: "inter_var" in n.mark)
    inter_usage = [{
        "type": T.get(G.entry(p).data_type["type"]),
        "declargs":{"var": f"*{{{{label.{G.entry(p).name}.name}}}}",
                    **G.entry(p).data_type},
        "consargs": [ "{{label." + G.entry(p).name + ".name}}" ,
                      "(*{{ label."+ G.entry(p).name +".name}})"],
        "descargs": [ "{{label." + G.entry(p).name + ".name}}" ,
                      G.entry(p).data_type.get("value")]
         } for p in inter_ports]
 
    snd_specs = [
        G.entry(p).port_type.sender_genspec(
            p, G.entry(p),
            [G.entry(o).name for o in G.connected_ports(p) if G.depth(o) == 2][0], T)
        for p in G.ports(node, select=lambda n: n.dir == ty.Dir.OUT)
    ]
    ############
    
    usage = (
        [snd_usage[0] for _, snd_usage, _, _ in snd_specs]    # constructor
        # + [snd_usage[1] for _, snd_usage, _, _ in snd_specs]  # declaration # TODO... why clashing with parent?
        + [T.gen_decl(**inter["declargs"]) for inter in inter_usage]
        + [inter["type"].gen_ctor(*inter["consargs"]) for inter in inter_usage]
        + ['{{ placeholder.code }}']
        + [inter["type"].gen_desctor(*inter["descargs"]) for inter in inter_usage]
        # + [snd_usage[2] for _, snd_usage, _, _ in snd_specs]  # marshalling # TODO... marshalling before sending
        + [snd_usage[3] for _, snd_usage, _, _ in snd_specs]  # destructor
    )
    inst = {
        "placeholder": entry.name,
        "block": Ref(_mangle_c_name(str(node))),
        "directive": ["expand"],  # TODO
        "bind": [{"label_to_label": bind} for bind in binds],
        "usage": ["\n".join(usage)],
        "_info": entry._info,
    }

    # proj = G.node_projection(node)
    # nx.nx_pydot.write_dot(proj, f"proj_{_mangle_c_name(str(node))}.dot")
    sched = list(nx.dfs_preorder_nodes(
        G.node_projection(node), source=node))[1:]
    # nx.nx_pydot.write_dot(nx.path_graph(sched), f"sched_{_mangle_c_name(str(node))}.dot")

    kerns = [_make_kernel_component(n, node, G, T) for n in sched if isinstance(G.entry(n), ty.KernelNode)]

    cp_insts = [inst for inst, _ in kerns] + [
        inst for _, _, snd_insts, _ in snd_specs for inst in snd_insts]

    comp = {
        "name": _mangle_c_name(str(node)),
        "type": {"module": "Generic", "name": "Composite"},
        "label": [{"name": G.entry(p).name} for p in inter_ports],
        "param": {"schedule": [inst["placeholder"] for inst in cp_insts]},
        "instance": cp_insts,
        "_info": entry._info,
    }
    return inst, (
        [comp]
        + [cp for _, cp in kerns]
        + [cp for _, _, _, snd_blocks in snd_specs for cp in snd_blocks]
    )


def _make_iport_reaction(pltf_name, actor_id, port_id, G, T):
    iport = G.entry(port_id)
    oports = [G.entry(p)
              for p in G.ports(actor_id, select=lambda p: p.dir == ty.Dir.OUT)]
    rcv_ports, rcv_proto, rcv_insts, rcv_blocks = iport.port_type.receiver_genspec(
        iport.name, pltf_name, T)
    proj = G.node_projection(actor_id)
    port_scenarios = [y
                      for x, y in proj.edges(actor_id)
                      for u, v in proj[x][y]["ports"]
                      if u == port_id and G.get_mark("scenario", y)]
    assert port_scenarios
    #############

    # TODO: ports between scenarios
    ports = (rcv_ports +
             [{"name": p.name} for p in  oports] +
             [{"name": G.entry(p).name, "usage": [G.get_mark("buff_name", p)]}
              for p in G.ports(actor_id, select=lambda p: p.dir == ty.Dir.IN)
              if p != port_id])

    proto = rcv_proto[:-1] + [
        rcv_proto[-1] + "\n ".join([
            T.gen_decl(f"* {{{{label.{p.name}.name}}}}", **p.data_type)
            for p in oports
        ]) + '\n {{ placeholder.code }}\n}']

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


def genspec(G, T, clean_ports, expand_actors, fuse_actors, typedefs, **kwargs):
    specs = {}

    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        name = pltf.name()
        glbs = G.ports(pltf, select=lambda p: "global_var" in p.mark)
        probes = [
            G.entry(p)
            for p in G.ports(pltf, select=lambda p: "probe_buffer" in p.mark)]
        timers = [
            G.entry(p)
            for p in G.ports(pltf, select=lambda p: isinstance(p.port_type, Timer))]
        atomports = [
            ({"name": "atom_table_len", "usage": ["DFL_dyn_atom_table_len"]},
             "static size_t "," = 0"),
            ({"name": "atom_table_inited", "usage": ["DFL_atom_table_inited"]},
             "static bool ", " = false"),
            ({"name": "atom_table", "usage": ["DFL_atom_table"]},
             "static DFL_atom_entry_t ", "[] = {\n" +
             "".join([
                 f"{{\"{p.mark['probe_buffer']}\", DFL_ATOM_INVALID_BIT}}\n"
                 for p in probes
             ]) + "}")]
        if "init_atom_table" in G.entry(pltf).mark:
            atomports += [
                ({"name": "dyn_table", "usage": ["DFL_dyn_atom_table"]},
                 "DFL_atom_entry_t *", " = 0"),
                ({"name": "dyn_table_inited", "usage": ["DFL_dyn_atom_table_inited"]},
                 "static bool ", " = false"),
            ]
        
        glbs_inst, glbs_comp = _make_global_inits(name, atomports, glbs, G, T)
        
        buffs = [G.entry(p).port_type.header_funcs(G.entry(p).name)
                 for p in G.ports(pltf, select=lambda p: isinstance(p.port_type, BlockBuffer))]
        buff_inst, buff_comp = ([j for i, c in buffs for j in i],
                                [j for i, c in buffs for j in c])
        
        stg1_inst, stg1_comp = _make_init_stage1(name, [], T)

        
        stg2_inst, stg2_comp = _make_init_stage2(name, probes, timers, G, T)

        iport = [
            G.entry(p).name
            for src in G.ports(pltf, select=lambda p: p.dir == ty.Dir.IN and isinstance(p.port_type, Socket))
            for p in G.connected_ports(src)
            if G.parent(p) and G.parent(G.parent(p)) and G.parent(G.parent(p)) == pltf
        ]
        icfg_inst, icfg_comp = _make_cfg_iport(name, iport, T)

        oport = [
            # (p, G.entry(p).name + "_socket")
            (p, G.entry(p).name)
            for p in G.ports(pltf, select=lambda p: p.dir == ty.Dir.OUT)
        ]
        ocfg_inst, ocfg_comp = _make_cfg_oport(name, oport, T)

        acfg_inst, acfg_comp = _make_cfg_atom(
            name,
            [a for a, _, _ in atomports],
            "init_atom_table" in G.entry(pltf).mark, T)

        # iffy
        osockets = [{"name": p[1]} for p in oport]  # , "usage": f"DFLBUF_{p[1]}"
        cfg_names = {"atom": acfg_comp["name"],
                     "inport": icfg_comp["name"],
                     "outport": ocfg_comp["name"]}

        main = {
            "name": "Main",
            "type": {"module": "Generic.Dfl", "name": "Main"},
            "requirement": {
                "include": T.requirements() + ["<stdio.h>"]
                + ['"DFL_core.h"', '"DFL_util.h"', '"dfl_cfg.h"',
                   '"dfl_evt.h"', '"dfl_thrd.h"', '"DflSys.h"']
                + [f'"{h}"' for h in typedefs.keys()]
            },
            "label": [a for a, _, _ in atomports] + osockets,
            "param": {"CFG": cfg_names},
            "prototype": [
                'int main(int argc, char * argv[]) { {{placeholder.code}} }'],
            "instance": [
                glbs_inst,
            ] + buff_inst + [
                stg1_inst,
                stg2_inst,
                icfg_inst,
                ocfg_inst,
                acfg_inst,
            ],
        }

        child_cps = []
        for actor in G.children(pltf, select=lambda n: isinstance(n, ty.ActorNode)):
            for port in G.ports(actor, select=lambda p: p.dir == ty.Dir.IN):
                child_cps.extend(_make_iport_reaction(name, actor, port, G, T))
        unique_child_cps = {cp["name"]: cp for cp in child_cps}
        cps = [main, glbs_comp, stg1_comp, stg2_comp, icfg_comp, ocfg_comp,
               acfg_comp] + buff_comp + list(unique_child_cps.values())
        

        preamble = {
            "module": name,
            "top": "Main",
        }

        defaults = [{
            "label": [{"usage": WithCreate(["p", "{{label.$p.name}}"])}],
            "instance": [{
                "bind": [{
                    "label_to_label": {
                        "usage": WithCreate(["p", "{{label.$p.name}}"])}}]
            },]
        },]
        
        specs[pltf.name()] = [preamble, Default([{"block": defaults}, {"block": cps}])]

    return specs


def typedefs(G, T, port_inference, **kwargs):
    types = dict()
    for port in [p for p in G.ir.nodes if isinstance(G.entry(p), ty.Port)]:
        typ = G.entry(port).data_type.get("type")
        if not typ or isinstance(typ, TypeABC):
            continue
        if typ not in types:
            types[typ] = []
        types[typ].append(port)

    deps = nx.DiGraph()
    for typ, ports in types.items():
        try:
            tydep = [t.ref for t in T.get(typ).select_types(of_class="ref")]
            nx.add_path(deps, tydep + [typ])
        except Exception as e:
            msg = f"Cannot load type '{typ}' needed for {ports}:\n{e}"
            raise ScriptError(msg, G.entry(ports[0]))
    tydefs = ""
    # print(list(nx.dfs_preorder_nodes(deps)))
    for typ in nx.dfs_preorder_nodes(deps):
        tydefs += T.gen_c_typedef(typ) + "\n"
        tydefs += "".join(T.gen_access_macros(typ)) + "\n"
    return {"types.h": tydefs}
