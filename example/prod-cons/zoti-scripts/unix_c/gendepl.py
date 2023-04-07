import networkx as nx

import zoti_graph.core as graph

_port_name_LUT = {}

def _port_spec(G, uid):
    entry = G.entry(uid)
    if entry.dir == graph.Dir.IN:
        actor_port_name = entry.name
    else:
        # print([G.entry(o).name for o in G.connected_ports(uid)
        #        if G.depth(G.commonAncestor(o, uid)) >= 1 and G.depth(o) > G.depth(uid)] )
        actor_port_name = [G.entry(o).name for o in G.connected_ports(uid)
                           if G.depth(G.commonAncestor(o, uid)) >= 1
                           and G.depth(o) > G.depth(uid)][0]  # TODO: wow!
    _port_name_LUT[uid] = actor_port_name
    port_dir = "InputNode" if entry.dir == graph.Dir.IN else "OutputNode"
    if entry.dir == graph.Dir.IN:
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
        actor_port_name,
        port_dir,
        {
            "data-type": repr(entry.data_type),
            "node-name": entry.name
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

    idx = 0
    cfg_port = 0xdf0
    idxs = {}
    for pltf in G.children(G.root, select=lambda n: isinstance(n, graph.PlatformNode)):
        entry = G.entry(pltf)
        idx += 1
        cfg_port += 1
        idxs[entry.name] = idx
        # print(idx, entry.name)
        node = [
            f"proc-{idx}-{entry.name}",
            entry.name,
            {
                "node-name": f"proc-{idx}-{entry.name}",
                "deployment-host": "localhost",
                "deployment-bin-file": f"{entry.name}.bin",
                "deployment-cfg-port": str(hex(cfg_port)),
                "deployment-in-window": idx,
            },
            {
                "name": f"proc-{idx}-{entry.name}",
                "nodes": [
                    _port_spec(G, p)
                    for p in G.ports(pltf, select=lambda x: x.dir != graph.Dir.INOUT) 
                ] + [
                    _atom_spec(G, p)
                    for p in G.ports(pltf, select=lambda x: "probe_buffer" in x.mark) 
                ]
            }
            
        ]
        
        depl["nodes"].append(node)

    idx = 0
    for pltf in G.children(G.root, select=lambda n: isinstance(n, graph.PlatformNode)):
        entry = G.entry(pltf)
        idx += 1
        for src, dst in G.node_edges(pltf, in_outside=True):
            src_entry = G.entry(src)
            dst_entry = G.entry(dst)
            if isinstance(src_entry, graph.Primitive) and src_entry.type == graph.PrimitiveTy.SYSTEM:
                depl["edges"].append([
                    "SYSTEM",
                    f"proc-{idx}-{entry.name}:{dst_entry.name}",
                    dst_entry.port_type.to_json()
                ])
            else:
                srcn_entry = G.entry(G.parent(src))
                depl["edges"].append([
                    f"proc-{idxs[srcn_entry.name]}-{srcn_entry.name}:{_port_name_LUT[src]}",
                    f"proc-{idx}-{entry.name}:{dst_entry.name}",
                    dst_entry.port_type.to_json()
                ])

    return depl
