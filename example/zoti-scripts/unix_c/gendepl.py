import networkx as nx

import zoti_graph.core as graph

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
        node = [
            f"proc-{idx}-{entry.name}",
            entry.name,
            {
                "node-name": f"proc-{idx}-{entry.name}",
                "deployment-host": "localhost",
                "deployment-bin-file": f"{entry.name}.bin",
                "deployment-cfg-port": str(hex(cfg_port)),
                "deployment-in-window": idx,
            }
        ]
        depl["nodes"].append(node)

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
                    f"proc-{idxs[srcn_entry.name]}-{srcn_entry.name}:{src_entry.name}",
                    f"proc-{idx}-{entry.name}:{dst_entry.name}",
                    dst_entry.port_type.to_json()
                ])

    return depl
