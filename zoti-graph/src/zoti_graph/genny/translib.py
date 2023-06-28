import networkx as nx
import logging as log

import zoti_graph.genny.core as ty
from zoti_graph.appgraph import AppGraph
from zoti_graph.core import Uid


def flatten(G: AppGraph, **kwargs):
    """This transformation flattens any composite nodes rendering a system
    description made of only basic nodes: platforms, actors and
    kernels. The only exception to this rule is actor scenarios which
    are kept clustered as composites for further processing. After
    this transformation the following holds:

    forall n in nodes(G):
      | n.parent is platform node ⇒ n is actor node
      | n.parent is actor node ⇒ n is kernel node or composite node marked "scenario"
      | n.parent is composite node ⇒ n is kernel node (i.e., belongs to a scenario)

    *NOTE*: node IDs remain unchanged, regardless of the new
    hierarchy.

    """
    # Mark scenario nodes to ignore
    scenarios = [
        scen
        for act in G.ir.nodes
        for scen in G.children(act)
        if isinstance(G.entry(act), ty.ActorNode)
        and isinstance(G.entry(scen), ty.CompositeNode)
    ]
    for n in scenarios:
        G.entry(n).mark["scenario"] = True

    # Flatten everything except scenarios
    def _recursive_flatten(parent: Uid, node: Uid):
        entry = G.entry(node)
        if isinstance(entry, ty.KernelNode):
            return
        for child in G.children(node):
            _recursive_flatten(node, child)
        if isinstance(entry, ty.CompositeNode) and not G.entry(node).mark.get("scenario"):
            G.uncluster(node, parent=parent)
            log.info(f"  - Unclustered {node} to {parent}")

    for child in G.children(G.root):
        _recursive_flatten(G.root, child)

    return True


def fuse_actors(G: AppGraph, flatten, **kwargs):
    """This transformation fuses all inter-dependent actors within the
    same timeline. After this transformation there will be no
    EVENT-like dependency between any two actors belonging to the same
    platform node, i.e., the following holds:

    foreach a, b in p, where p is platform node in nodes(G):
      | there exists e in edges(G) such that e.src = a and e.dst = b
        => e.kind = STORAGE
      | => (inputs(a) in p) is disjoint from (inputs(b) in p)

    *TODO*: check if fusing on ``Relation.EVENT`` is appropriate

    *TODO*: fuse FSMs

    """
    def _fuse_children(proj, _nodes, _edges, msg, under=[]):
        deps = nx.subgraph_view(proj, filter_node=_nodes, filter_edge=_edges)
        for cluster in list(nx.connected_components(deps.to_undirected())):
            if len(cluster) <= 1:
                continue
            depgraph = proj.subgraph(cluster)
            if under:
                fused_id = under[0]
            else:
                fused_id, _, _ = list(depgraph.edges)[0]
            parsed_dep = list(nx.edge_bfs(depgraph, fused_id, orientation="ignore"))
            log.info(f"{msg} {cluster} under {fused_id}")
            for u, v, idx, orientation in parsed_dep:
                fuse_edgs = [k for s, t, k in proj.edges(data="ports")
                             if (s, t) == (u, v) or (s, t) == (v, u)]
                if orientation == "forward":
                    G.fuse_nodes(fused_id, v, fuse_edgs)
                else:
                    G.fuse_nodes(fused_id, u, fuse_edgs)
            yield fused_id

    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        # Double check if SIDE connections are marked (or at least have been disconnected)
        for actor in G.children(pltf):
            for port in G.ports(actor, select=lambda p: p.kind == ty.Dir.SIDE):
                for s, d in G.port_edges(port):
                    if "storage" not in G.edge(s, d).mark:
                        raise Exception("found non-marked connection between SIDE ports")

        proj = G.node_projection(pltf, no_parent_ports=True)
        fused_actors = _fuse_children(
            proj,
            _nodes=lambda n: not isinstance(n, ty.BasicNode),
            _edges=lambda u, v, k: "storage" not in G.edge(*proj[u][v][k]["ports"]).mark,
            msg="  - Fusing actors in the same timeline",
            under=G.children(pltf, select=lambda n: not n.mark)
        )
        for actor in fused_actors:
            # Searching and fusing FSMs
            fsms = G.children(actor, select=lambda n: "detector" in n.mark)
            if len(fsms) > 1:
                log.info(f"  - fusing FSMs {fsms}")
                raise NotImplementedError  # TODO

            # Fusing scenarios (OBS: force yield)
            sc_proj = G.node_projection(actor, no_parent_ports=True)  # !!!
            list(_fuse_children(
                sc_proj,
                _nodes=lambda n: G.entry(n).mark.get("scenario"),
                _edges=lambda u, v, k: True,
                msg="  - Fusing scenarios"))
    return True
