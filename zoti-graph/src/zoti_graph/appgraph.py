from copy import deepcopy
from typing import Any, List, Tuple, Optional

import networkx as nx

import zoti_graph.core as ty
import zoti_graph.util as util
from zoti_graph.core import Uid
from zoti_graph.exceptions import EntryError


class AppGraph:
    """A ZOTI application graph. Its methods are meant as general purpose
    utilities, however for more advanced functionality one might apply
    `NetworkX <https://networkx.org/documentation/stable/index.html>`_
    algorithms directly on its ``ir`` member.

    """

    root: Uid
    """The ID of the root node"""

    ir: nx.DiGraph
    """Internal representation of a ZOTI model as simple annotated digraph. """

    def __init__(self, root=Uid()):
        self.ir = nx.DiGraph()
        self.root = root if isinstance(root, Uid) else Uid(root)

    def reset(self, root):
        """Resets the current application graph and sets the *root* node ID."""
        self.ir = nx.DiGraph()
        self.root = root

    def entry(self, uid: Uid) -> Any:
        """Returns a ZOTI graph node or port entry with a given identifier.

        """
        try:
            return self.ir.nodes[uid][ty.ATTR_ENT]
        except Exception:
            raise KeyError(f"node {uid}")

    def edge(self, u: Uid, v: Uid) -> Any:
        """Returns a ZOTI edge entry with a given identifier.

        """
        try:
            return self.ir[u][v][ty.ATTR_ENT]
        except Exception:
            raise KeyError(f"edge ({u}, {v})")

    def decouple(self, uid) -> None:
        """Makes a deepcopy of an entry and replaces the original. Useful
        after replication-based transformations (e.g. port inference).

        """
        ret = self.ir.nodes.get(uid)
        new_entry = deepcopy(ret[ty.ATTR_ENT])
        ret[ty.ATTR_ENT] = new_entry

    def new(self, uid: Uid, obj: Any) -> Uid:
        """Adds a new ZOTI node or port object to the current app
        graph. Returns *uid* for chaining it with other functions (see
        :meth:`register_child` or
        :meth:`register_port`)

        """
        self.ir.add_node(uid, **{ty.ATTR_ENT: obj})
        return uid

    def register_port(self, parent_id: Uid, port_id: Uid) -> Uid:
        """Registers a pre-created port to a node (see :meth:`new`). Returns
        *port_id*.

        """
        self.ir.add_edge(parent_id, port_id, **{ty.ATTR_REL: ty.Rel.PORT})
        return port_id

    def register_child(self, parent_id: Uid, child_id: Uid) -> Uid:
        """Registers a pre-created child node to a parent (see
        :meth:`new`). Returns *child_id*.

        """
        self.ir.add_edge(parent_id, child_id, **{ty.ATTR_REL: ty.Rel.CHILD})
        return child_id

    def connect(self, srcport, dstport, edge=ty.Edge, recursive=True):
        """Connects two ports through an edge. If `recursive` is set to
        ``True`` then it recursively creates intermediate ports and
        connections if the source and destination nodes belong to
        different parents. If an *edge* entry is provided then all the
        new edges will be associated with it, otherwise they will have
        no entry.

        .. image:: assets/zoti_graph_connect.png

        """

        def _weight(u, v, kwargs):
            return (1 if kwargs[ty.ATTR_REL] & ty.Rel.TREE else 9999)

        def _reg_port(port, node, templ):  # direction):
            newport = util.unique_name(
                node.withPort(port.name()),
                self.ports(node),
                modifier=lambda u, s: u.withSuffix(s),
            )
            newentry = deepcopy(templ)
            newentry.name = newport.name()
            self.new(newport, newentry)
            self.register_port(node, newport)
            return newport

        attr = {ty.ATTR_REL: ty.Rel.GRAPH, ty.ATTR_ENT: edge}

        try:
            if recursive:
                via = self.commonAncestor(srcport, dstport)
                srcentry, dstentry = (self.entry(srcport), self.entry(dstport))
                srcfamily = nx.shortest_path(
                    self.ir, source=via, target=srcport, weight=_weight)[1:-2]
                dstfamily = nx.shortest_path(
                    self.ir, source=via, target=dstport, weight=_weight)[1:-2]
                path = ([_reg_port(srcport, n, srcentry) for n in reversed(srcfamily)] +
                        [_reg_port(dstport, n, dstentry) for n in dstfamily])
                edges = list(zip([srcport] + path, path + [dstport]))
                self.ir.add_edges_from(edges, **attr)
            else:
                self.ir.add_edge(srcport, dstport, **attr)
        except Exception as e:
            raise ValueError(
                f"Cannot connect {srcport} to {dstport}.\n{str(e)}")

    def ports(self, parent_id, select=lambda x: True) -> List[Uid]:
        """Returns a list of IDs for all the ports of this parent. The result
        can be filtered by passing a *select* function on
        :class:`zoti_graph.core.Port` entries.

        """
        try:
            return [
                v
                for u, v in self.ir.out_edges(parent_id)
                if self.ir[u][v][ty.ATTR_REL] == ty.Rel.PORT
                if select(self.ir.nodes[v][ty.ATTR_ENT])
            ]
        except Exception:
            raise KeyError(f"node {parent_id}")

    def children(self, parent_id, select=lambda x: True) -> List[Uid]:
        """Returns a list of IDs for all the children of this parent. The
        result can be filtered by passing a *select* function on
        entries derived from :class:`zoti_graph.core.NodeABC`.

        """
        try:
            return [
                v
                for u, v in self.ir.out_edges(parent_id)
                if self.ir[u][v][ty.ATTR_REL] == ty.Rel.CHILD
                if select(self.ir.nodes[v][ty.ATTR_ENT])
            ]
        except Exception:
            raise KeyError(f"node {parent_id}")

    def parent(self, node_id) -> Optional[Uid]:
        """Returns the ID for this node's parent. If this node has no parent
        it returns None.

        """
        try:
            parents = [
                u
                for u, v in self.ir.in_edges(node_id)
                if self.ir[u][v][ty.ATTR_REL] & ty.Rel.TREE
            ]
            return parents[0] if parents else None
        except Exception:
            raise KeyError(f"node {node_id}")

    def commonAncestor(self, this: Uid, that: Uid) -> Optional[Uid]:
        """Returns the ID of the common ancestor between *this* and *that*. If
        they have no common ancestor it returns None.

        """
        while this != that and this is not None and that is not None:
            if this > that:
                this = self.parent(this)
            else:
                that = self.parent(that)
            if this == that:
                return this
        return None

    def port_edges(self, port_id, which="all") -> List[Tuple[Uid, Uid]]:
        """Returns all edge identifiers connected to/from *port_id*. Can
        filter the in/out edges with argment *which* that can be
        ``in``, ``out`` or ``all``.

        """
        assert which in ["in", "out", "all"]
        try:
            return [
                (u, v)
                for u, v in self.ir.in_edges(port_id)
                if self.ir[u][v][ty.ATTR_REL] & ty.Rel.GRAPH
            ] if which in ["in", "all"] else [] + [
                (u, v)
                for u, v in self.ir.out_edges(port_id)
                if self.ir[u][v][ty.ATTR_REL] & ty.Rel.GRAPH
            ] if which in ["out", "all"] else []
        except Exception:
            raise KeyError(f"port {port_id}")

    def node_edges(self, node_id, which="all+all") -> List[Tuple[Uid, Uid]]:
        """Returns all the edge identifiers entering or exiting the *ports* of
        this node, as list of ID pairs.

        .. image:: assets/zoti_graph_side_edges.png
            :scale: 120%

        """
        assert "+" in which
        dirc, view = tuple(which.split("+"))
        assert dirc in ["in", "out", "all"]
        assert view in ["inside", "outside", "all"]
        in_inside = dirc in ["in", "all"] and view in ["inside", "all"]
        in_outside = dirc in ["in", "all"] and view in ["outside", "all"]
        out_inside = dirc in ["out", "all"] and view in ["inside", "all"]
        out_outside = dirc in ["out", "all"] and view in ["outside", "all"]
        # below apply BA+C!A == (B+!A)(C+A)
        try:
            return [
                (u, v)
                for port in self.ports(node_id)
                for u, v in self.ir.in_edges(port)
                if self.ir[u][v][ty.ATTR_REL] == ty.Rel.GRAPH
                if (out_inside or not self.has_ancestor(u, node_id))
                if (in_outside or self.has_ancestor(u, node_id))
            ] + [
                (u, v)
                for port in self.ports(node_id)
                for u, v in self.ir.out_edges(port)
                if self.ir[u][v][ty.ATTR_REL] == ty.Rel.GRAPH
                if (in_inside or not self.has_ancestor(v, node_id))
                if (out_outside or self.has_ancestor(v, node_id))
            ]
        except Exception:
            raise KeyError(f"node {node_id}")

    def connected_ports(self, port, graph=None) -> nx.Graph:
        """Returns a path graph representing the journey between two leaf
        nodes' ports passing through a given *port*, see drawing. The
        search can be minimized by passing a subgraph to the *graph*
        argument containing the desired path.

        .. image:: assets/zoti_graph_connected_ports.png

        """
        graph = self.only_graph()
        return graph.subgraph(nx.shortest_path(graph.to_undirected(), port))

    def end_ports(self, port, graph=None) -> List[ty.Uid]:
        """Variant of :meth:`connected_ports` which returns a list with end
        ports insdead of the entire connected subgraph, i.e., ports
        whose connectivity degree is 1. In the previous example this
        would mean ``["/node1/node2/^o1", "/node3/node4/^i1"]``

        """
        conn = self.connected_ports(port, graph)
        return [x for x in conn.nodes() if conn.degree(x) == 1]

    def is_leaf(self, uid: Uid) -> bool:
        """ Checks if a given node is a leaf(i.e., has no children) """
        return not self.children(uid)

    # def has_attr(self, uid, attr, val) -> bool:
    #     """Checks if the entry for *uid* has an attribute *attr* of value *val*."""
    #     return getattr(self.entry(uid), attr, None) == val

    def has_ancestor(self, uid: Uid, ancestor: Uid) -> bool:
        """Checks if *ancestor* is indeed an ancestor of *uid*."""
        parent = self.parent(uid)
        if not parent:
            return False
        elif parent == ancestor:
            return True
        else:
            return self.has_ancestor(parent, ancestor)

    def depth(self, uid) -> int:
        """Checks at which depth in the hierarchy tree *uid* is found relative
        to the global root."""
        dph = 0
        parent = self.parent(uid)
        while parent:
            dph += 1
            parent = self.parent(parent)
        return dph

    def bypass_port(self, port, ensure_fanout=False):
        """Removes the port with a given ID and reconnects its upstream to its
        downstream connections. Useful when flattening hierarchies,
        e.g., unclustering the nodes under a ``CompositeNode``.

        """
        if port not in self.ir:
            return

        delete = True
        new_connections = []
        for ui, vi in self.port_edges(port, which="in"):
            edge = self.edge(ui, vi)
            for uo, vo in self.port_edges(port, which="out"):
                if ensure_fanout and self.depth(uo) != self.depth(vo):
                    delete = False
                else:
                    self.ir.remove_edge(uo, vo)
                    self.connect(ui, vo, edge, recursive=False)
                    new_connections.append((ui, vo))
        if delete:
            self.ir.remove_node(port)
        return new_connections

    def copy_tree(self, root, new_name) -> Uid:
        """Copies the entire subgraph under an arbitrary *root* node to
        sibling a new sibling with *new_name*. Returns the ID of this
        new sibling.

        *ATTENTION:* all the copied child nodes will refer to the
        original entries and will need to be :meth:`decouple` d first
        if any local alteration is intended.

        """
        # ATTENTION: children need decoupling
        assert root.parent()
        new_root = root.parent().withNode(new_name)
        all_children = [c for c in self.ir.nodes if self.has_ancestor(c, root)]
        all_children.append(root)
        G = self.ir.subgraph(all_children)
        mapping = {n: n.replaceRoot(root, new_root) for n in G.nodes()}
        new_G = nx.relabel_nodes(G, mapping, copy=True)
        self.ir.update(new_G)
        assert new_root in self.ir.nodes()
        self.register_child(root.parent(), new_root)
        self.decouple(new_root)
        new_entry = self.entry(new_root)
        new_entry.name = new_name
        return new_root

    def remove_tree(self, root, with_root=True):
        """Removes the entire subgraph under an arbitrary *root*
        node. *with_root* toggles whether or not the root node will
        also be deleted.

        """
        assert root.parent()
        all_children = [c for c in self.ir.nodes if self.has_ancestor(c, root)]
        if with_root:
            all_children.append(root)
        self.ir.remove_nodes_from(all_children)

    def cluster(self, node, children):
        """Clusters the *children* nodes represented with a list of IDs under
        a (fully-created and instantiated) *node*. Both *node* and
        *children* need to belong the same parent, otherwise an error
        is thrown.

        """

        parent = self.parent(node)
        for child in children:
            if self.parent(child) != parent:
                msg = f"Cannot cluster {list(children)} under {node}."
                msg += " They do not have the same parent."
                raise ValueError(msg)

        clust = self.ir.subgraph(children)
        for child in clust.nodes():
            self.ir.remove_edge(parent, child)
            self.register_child(node, child)
            outside = [
                (u, v)
                for u, v in self.node_edges(child, which="all+outside")
                if not (clust.has_node(self.parent(u)) and
                        clust.has_node(self.parent(v)))
            ]
            for u, v in outside:
                edge = self.edge(u, v)
                self.connect(u, v, edge=edge, recursive=True)
                self.ir.remove_edge(u, v)

    def uncluster(self, node, parent=None):
        """Unclusters all children of a node and reconnects them in the
        context of *parent*. If *parent* is not provided, then it is
        assumed to be the parent of *node*. Finally, *node* is removed
        along with all its ports.

        """
        parent = parent if parent else self.parent(node)
        if parent is None:
            return  # TODO: exception maybe?
        for port in self.ports(node):
            self.bypass_port(port)
        for child in self.children(node):
            self.register_child(parent, child)
        self.ir.remove_node(node)

    def fuse_nodes(self, n1, n2, along_edges=None):
        """Fuses two nodes *n1* and *n2* into a single node containing all
        children and all ports belonging to both actors. The fused
        node will bear the name and ID of *n1*. The argument
        *along_edges* can be used to skip searching which edges
        connect *n1* and *n2*.

        *ATTENTION:* rather unstable! It is the caller's job to check that the
        resulting graph is consistent.

        """
        if along_edges is None:
            along_edges = [
                (u, v)
                for u, v in self.only_graph(with_ports=False).edges
                if self.parent(u) in [n1, n2] and self.parent(v) in [n1, n2]
            ]
        # print("FUSING NODES", n1, n2)
        for src, dst in along_edges:
            self.bypass_port(src, ensure_fanout=True)
            self.bypass_port(dst)
        for port in self.ports(n2):
            self.register_port(n1, port)
            # print("REGISTERED PORT", port, "TO", n1)
        for child in self.children(n2):
            ch = self.register_child(n1, child)
            # print("REGISTERED NODE", ch, "TO", n1)
        self.ir.remove_node(n2)
        # print("REMOVED", n2)

    def node_projection(self, parent) -> nx.MultiDiGraph:
        """Displays the projection of nodes upon a single level of hierarchy
        for all first children of *parent*. The first and the last
        nodes are the parent's ports.

        The projection view is a multi-digraph (i.e., directed graph
        with possibly parallel edges), where each edge contain a
        *srcport* and *dstport* enttry.

        .. image:: assets/zoti_graph_projection.png

        """
        def _filter(n1, n2):
            return self.ir[n1][n2].get(ty.ATTR_REL) == ty.Rel.GRAPH

        nodes = set(self.ports(parent) + self.children(parent) + [
            p for chld in self.children(parent) for p in self.ports(chld)])
        cluster = nx.subgraph_view(
            self.ir, filter_node=lambda n: n in nodes, filter_edge=_filter
        )
        view = nx.MultiDiGraph()
        for u, v in cluster.edges:
            src = u if self.parent(u) == parent else self.parent(u)
            dst = v if self.parent(v) == parent else self.parent(v)
            srcport = None if self.parent(u) == parent else u
            dstport = None if self.parent(v) == parent else v
            view.add_edge(src, dst, srcport=srcport, dstport=dstport)

        return view

    def _fast_filter_nodes(self, root, with_ports):
        # hopefully better performance
        def _nodes_wo_ports_wo_root(n):
            return not isinstance(n, ty.Port)

        def _nodes_wo_ports_w_root(n):
            return self.has_ancestor(n, root) and not isinstance(n, ty.Port)

        def _nodes_w_ports_wo_root(n):
            return True

        def _nodes_w_ports_w_root(n):
            return self.has_ancestor(n, root)

        if root and with_ports:
            return _nodes_w_ports_w_root
        elif not root and with_ports:
            return _nodes_w_ports_wo_root
        elif root and not with_ports:
            return _nodes_wo_ports_w_root
        else:
            return _nodes_wo_ports_wo_root

    def only_tree(self, root=None, with_ports=True) -> nx.DiGraph:
        """Returns a graph view representing only the hierarchy between
        nodes. If *root* is provided, only the sub-tree under it is
        captured by the view. *with_ports* toggles whether ports are
        included in this view or not.

        """

        def _edges(n1, n2):
            return self.ir[n1][n2][ty.ATTR_REL] & ty.Rel.TREE

        return nx.subgraph_view(
            self.ir,
            filter_node=self._fast_filter_nodes(root, with_ports),
            filter_edge=_edges)

    def only_graph(self, root=None, with_ports=True) -> nx.DiGraph:
        """Returns a graph view representing only the application graph. If
        *root* is provided only the sub-graph under it is included in the
        view. *with_ports* toggles whether ports are included in this view or
        not.

        """

        def _edges(n1, n2):
            return self.ir[n1][n2][ty.ATTR_REL] == ty.Rel.GRAPH

        return nx.subgraph_view(
            self.ir,
            filter_node=self._fast_filter_nodes(root, with_ports),
            filter_edge=_edges)

    def sanity(self, rule, *element_id):
        """Performs sanity checking on the graph element identified as
        *element_id* (single argument for node, double argument for
        edge).

        *rule* is an assertion function taking as arguments the
        current graph and *element_id* (see the `Sanity Rules
        <the-zoti-graph-model.html#sanity-rules>`__)

        """
        try:
            rule(self, *element_id)
        except AssertionError:
            msg = "Sanity check failed for "
            if len(element_id) < 2:
                msg += f"node {element_id[0]}"
                obj = self.entry(*element_id)
            else:
                msg += f"edge {tuple(element_id)}"
                obj = self.edge(*element_id)
            msg += f"during rule '{rule.__name__}':"
            raise EntryError(msg, obj=obj)
