from itertools import chain

from zoti_graph.core import Rel, ATTR_REL
import zoti_graph.genny as ty


def _flatten(n, G):
    entry = G.entry(n)
    if isinstance(entry, ty.BasicNode):
        return []
    if not isinstance(entry, ty.CompositeNode):
        return [n]
    return list(chain.from_iterable([_flatten(c, G) for c in G.children(n)]))


def _non_composite_children(n, G):
    return list(chain.from_iterable([_flatten(c, G) for c in G.children(n)]))


def _non_composite_parent(n, G):
    parent = n.parent()
    assert n != parent
    if isinstance(G.entry(parent), ty.CompositeNode):
        return _non_composite_parent(parent, G)
    return parent


def edge_direction(G, u, v):
    """Edge direction should be consistent with the hierarchy of its connecting elements.

    forall u,v in edges(G)
      | u is basic and v is not basic ⇒ v.kind ∈ {IN}
      | v is basic and u is not basic ⇒ u.kind ∈ {OUT}
      | node(u) and node(v) are siblings ⇒ u.dir ∈ {OUT, SIDE} & v.dir ∈ {IN, SIDE}
      | node(u) is parent for node(v) ⇒ u.dir = v.dir ∈ {IN, INOUT}
      | node(u) is child for node(v) ⇒ u.dir = v.dir ∈ {OUT, INOUT}

    """
    port_u, port_v = (G.entry(u), G.entry(v))
    if isinstance(port_u, ty.BasicNode) and not isinstance(port_v, ty.BasicNode):
        assert port_v.has_dir_in()  # in
        return
    if isinstance(port_v, ty.BasicNode) and not isinstance(port_u, ty.BasicNode):
        # assert port_u.kind == ty.Dir.OUT  # out
        assert port_u.has_dir_out()  # out
        return

    node_u, node_v = (u.parent(), v.parent())
    if node_u == node_v:
        # same node, means that the ports are short-circuited
        assert port_u.has_dir_in()
        assert port_v.has_dir_out()
    elif node_u.parent() == node_v.parent():
        # same parent means different directions
        assert port_u.has_dir_out()  # out, side
        assert port_v.has_dir_in()  # in, side
    elif node_u < node_v:
        # different parent means same directions
        assert port_u.has_dir_in()
        assert port_v.has_dir_in()
    elif node_u > node_v:
        # different parent means same directions
        assert port_u.has_dir_out()  # out, inout
        assert port_v.has_dir_out()  # out, inout


def edge_hierarchy(G, u, v):
    """Edges can only connect sibling nodes or child nodes to their parents.

    forall u,v in edges(G)
      | node(u) and node(v) have different parents ⇒
           node(u) = node(v).parent ⊻ node(v) = node(u).parent

    """
    node_u, node_v = (u.parent(), v.parent())
    if node_u.parent() != node_v.parent():
        # if not the same parent, then they are parent-child
        # same rule is true for intrinsics as well
        assert (node_u == node_v.parent()) ^ (node_u.parent() == node_v)


def edge_sibling_kind(G, u, v):
    """Interconnected sibling nodes (except intrinsics and ignoring the
    hierarchy of composites) are of the same kind.

    forall u,v in edges(G) where node(u), node(v) are not intrinsic
      | node(u) and node(v) have same parent ⇒
           flatten(node(u)) ⋃ flatten(node(v)) are all of the same kind

    """
    if isinstance(G.entry(u), ty.BasicNode):
        return
    if isinstance(G.entry(v), ty.BasicNode):
        return
    node_u, node_v = (u.parent(), v.parent())
    if node_u.parent() == node_v.parent():
        flattened = _flatten(node_u, G) + _flatten(node_v, G)
        if flattened:
            first_type = type(G.entry(flattened[0])).__name__
            for n in flattened[1:]:
                curr_type = type(G.entry(n)).__name__
                assert first_type == curr_type


def node_consistent_tree(G, n):
    """All nodes except for the root node have only one parent.

    forall n in nodes(G) - root(G):
      | ⇒ len(n.parents) = 1
    """
    if n == G.root:
        return
    parents = [
        u for u, v in G.ir.in_edges(n)
        if G.ir[u][v][ATTR_REL] & Rel.TREE
    ]
    assert len(parents) == 1


def node_platform_hierarchy(G, n):
    """Ignoring the hierarchy of composites all platform nodes contain
    only actor nodes.

    forall n in nodes(G) where n is platform node:
      | ⇒ n.parent is composite node
      | ⇒ all first children which are not composite
             are only intrinsic or actor nodes

    """
    entry = G.entry(n)
    if not isinstance(entry, ty.PlatformNode):
        return
    parent = G.entry(n.parent())
    assert isinstance(parent, ty.CompositeNode)

    children = _non_composite_children(n, G)
    for child in children:
        assert isinstance(G.entry(child), ty.ActorNode)


def node_actor_hierarchy(G, n):
    """Ignoring the hierarchy of composites, all actor nodes belong to a
    platform node and contain only kernel nodes.

    forall n in nodes(G) where n is actor node:
      | ⇒ the first parent which is not composite is platform node
      | ⇒ all first children which are not composite are only intrinsic or kernel nodes

    """
    entry = G.entry(n)
    if not isinstance(entry, ty.ActorNode):
        return
    parent = G.entry(_non_composite_parent(n, G))
    assert isinstance(parent, ty.PlatformNode)

    children = _non_composite_children(n, G)
    for child in children:
        assert isinstance(G.entry(child), ty.KernelNode)


def node_kernel_hierarchy(G, n):
    """Ignoring the hierarchy of composites, all kernel nodes belong to an
    actor node.

    forall n in nodes(G) where n is kernel node:
      | ⇒ the immediate parent which is not composite is actor node
      | ⇒ no child nodes exist

    """
    entry = G.entry(n)
    if not isinstance(entry, ty.KernelNode):
        return
    parent = G.entry(_non_composite_parent(n, G))
    assert isinstance(parent, ty.ActorNode)

    children = G.children(n)
    assert len(children) == 0


def node_actor_consistency(G, n):
    # checks name consistency
    # checks decoupled scenarios

    entry = G.entry(n)
    if not isinstance(entry, ty.ActorNode):
        return
    if entry.detector is None:
        return
    if entry.detector.preproc:
        assert n.withNode(entry.detector.preproc) in G.children(n)
    for port in entry.detector.inputs:
        assert G.ir.has_node(n.withPath(ty.Uid(port)))
    if not entry.detector.states and entry.detector.expr:
        assert len(entry.detector.expr) == 1
    if entry.detector.states and entry.detector.expr:
        for state, expr in entry.detector.expr.items():
            assert state in entry.detector.states
            if "goto" in expr:
                assert expr["goto"] in entry.detector.states
    if entry.detector.scenarios is None:
        return
    for scen in entry.detector.scenarios.values():
        assert n.withNode(scen) in G.children(n)
        # TODO: scenarios are decoupled using projection


# def port_dangling(G, p):
#     """There is no dangling port in the graph.

#     forall p in ports(G):
#       | node(p) is kernel node ⇒ exists e in edges(G) such that p = e.src or p = e.dst
#       | p is inout port ⇒ exists e1, e2 in edges(G) such that p = e1 ∩ e2
#       | otherwise ⇒ exists e1, e2 in edges(G) such that p = e1.src and p = e2.dst
#     """
#     node = G.entry(p.parent())
#     port = G.entry(p)
#     inedges = G.port_edges(p, which="in")
#     outedges = G.port_edges(p, which="out")

#     if isinstance(node, ty.KernelNode):
#         pass  # TODO, handle detector preproc
#         # assert len(inedges) > 0 or len(outedges) > 0
#     elif isinstance(port, ty.Port) and port.kind == ty.Dir.SIDE:
#         assert len(inedges) + len(outedges) > 1
#     else:
#         assert len(inedges) > 0 and len(outedges) > 0


def port_dangling(G, p):
    """'Dangling port' means either an event port which is not connected
    (is triggered by nothing or triggers nothing) or a side-effect
    port which is not exposed at the actor level (that might be
    ignored).

    """
    if G.entry(p).kind == ty.Dir.SIDE:
        assert any([
            isinstance(G.entry(G.parent(q)), ty.ActorNode)
            for q in G.connected_ports(p)
        ])
    else:
        assert all([
            isinstance(G.entry(G.parent(q)), ty.KernelNode) or
            isinstance(G.entry(q), ty.BasicNode)
            for q in G.end_ports(p)
        ])
