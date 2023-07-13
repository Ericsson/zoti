from copy import deepcopy
import networkx as nx
import logging as log
import zoti_graph.genny as ty
import zoti_graph.util as util

import ports


def port_inference(G, T, **kwargs):
    """Resolves and fills in the *data_type*, *port_type* adn *mark*
    fields for all groups of interconnected ports. Port resolution is
    defined in :module:`zoti_tran.unix_c.ports`. After this
    transformation the following holds:

    forall p in ports(G)
      | p.data_type ∈ zoti_ftn.backend.c
      | p.port_type ∈ ports

    """
    ag = G.only_graph().to_undirected()
    for conn in list(nx.connected_components(ag)):
        pids = [p for p in conn if isinstance(G.entry(p), ty.Port)]
        pents = [G.entry(p) for p in pids]
        if not pids:
            continue
        port_attr = ports.merge_attrs(pents, "port_type", "Port type argument mismatch: ")
        data_attr = ports.merge_attrs(pents, "data_type", "Data type argument mismatch: ")
        orig_mark = ports.merge_attrs(pents, "mark", "Mismatched markings: ")
        for p in pids:
            G.update(p, ports.make_port_type(port_attr, G.entry(p)))
            G.entry(p).make_data_type(T, data_attr)
            G.entry(p).make_markings(orig_mark)
        log.info(f"  - Resolved {pids}")

    return True  # Byproduct is a flag


def prepare_platform_ports(G, T, port_inference, **kwargs):
    """Updates all input ports of platform nodes to reflect the buffer
    type required by the port receiver, respectively the socket port
    required by the sender.

    """
    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        # change data types of input ports. TODO: deprecated
        for iport in G.ports(pltf, select=lambda p: p.kind == ty.Dir.IN):
            G.entry(iport).update_input_buffer_type(T)
            log.info(f"  - Changed type for in port: {iport}")

        # alter exit ports to reflect socket variables
        for oport in G.ports(pltf, select=lambda p: p.kind == ty.Dir.OUT):
            socket_id = oport.withSuffix(f"{pltf.name()}_socket")
            # for p in G.connected_ports(oport):
            #     if G.has_ancestor(p, pltf):
            #         G.decouple(p)
            #         G.entry(p).mark["socket_port"] = socket_id
            socket_port = G.entry(oport).new_output_socket_port(socket_id, T)
            G.register_port(pltf, G.new(socket_id, socket_port))
            log.info(f"  - Added global out port for: {oport}")
    return True


def prepare_side_ports(G, port_inference, **kwargs):
    """ """
    def _make_global(pltf, name, port) -> str:
        glb_key = util.unique_name(pltf.withPort(name), G.ports(pltf),
                                   modifier=lambda u, s: u.withSuffix(s))
        newport = deepcopy(port)
        newport.name = f"_{pltf.name()}_{glb_key.name()}".replace(".", "_")
        G.register_port(pltf, G.new(glb_key, newport))
        G.entry(glb_key).mark["global_var"] = True
        return newport.name

    def _remove_selected_ports(connected, select):
        to_remove = [p for p in connected.nodes() if select(p)]
        for p in to_remove:
            G.ir.remove_node(p)
        return to_remove

    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        for actor in G.children(pltf, select=lambda n: isinstance(n, ty.ActorNode)):
            ports_to_remove = set()
            for port in G.ports(actor):
                conn = G.connected_ports(port)
                ends = G.end_ports(port, graph=conn)
                entry = G.entry(port)

                # sync names of interconneted storage ports and make globals for them
                if (G.entry(port).kind == ty.Dir.SIDE
                    # and not G.entry(port).mark.get("global_var")
                    ):
                    glb_name = _make_global(pltf, entry.name, entry)
                    for p in [e for e in ends if isinstance(G.entry(e), ty.Port)]:
                        G.entry(p).name = glb_name
                        G.entry(p).mark["global_var"] = True
                    log.info(
                        f"  - Promoted to global '{glb_name}': {conn.nodes}")

                    # remove all intermediate "side" connections
                    def _to_remove(p):
                        return not isinstance(G.entry(G.parent(p)), ty.KernelNode)
                    rmd = _remove_selected_ports(conn, _to_remove)
                    log.info(f"  - Removed intermediate storage ports {rmd}")

    return True


def prepare_intermediate_ports(G, port_inference, **kwargs):
    def _new_intermediate_connection(parent, src, dst):
        edge = G.edge(src, dst)
        # check if there is already a CompositeNode's port which can act as a via
        exist = [v for u, v in G.ir.out_edges(src) if G.parent(v) == parent]
        if exist:
            inter = exist[0]
            # TODO: does it need to be marked?
        else:
            # othewise make a new one and connect to it
            pentry = deepcopy(G.entry(dst))
            inter = parent.withPort(pentry.name)
            G.register_port(parent, G.new(inter, pentry))
            G.entry(inter).mark["inter_var"] = True
            pentry.dir = ty.Dir.SIDE
            for new_src in [u for u, v in G.port_edges(dst, which="in")]:
                G.connect(new_src, inter, edge, recursive=False)
        G.ir.remove_edge(src, dst)
        G.connect(inter, dst, edge, recursive=False)
        return inter

    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        for actor in G.children(pltf, select=lambda n: isinstance(n, ty.ActorNode)):
            proj = G.node_projection(actor, no_parent_ports=True)
            for src_scen, dst_scen, ports in proj.edges(data="ports"):
                inter = _new_intermediate_connection(actor, *ports)
                log.info(f"  - Using {inter} as intemediate between {ports}")
            for scen in G.children(actor, select=lambda n: isinstance(n, ty.CompositeNode)):
                # expose intermediate variables in scenarios
                proj = G.node_projection(scen, no_parent_ports=True)
                for src_kern, dst_kern, ports in proj.edges(data="ports"):
                    inter = _new_intermediate_connection(scen, *ports)
                    log.info(
                        f"  - Using {inter} as intemediate between {ports}")

    return True


def expand_actors(G, T, **kwargs):
    """Expands actor descriptions to their explicit basic
    components. Assumes actors have been checked for consistency.

    """

    def _port_copy(name, parent, entry):
        return G.register_port(parent, G.new(parent.withPort(name), deepcopy(entry)))

    def _cluster_underneath(name, parent, schedule, info):
        composite = parent.withNode(name)
        composite_entry = ty.CompositeNode(name, info=info,)
        G.register_child(parent, G.new(composite, composite_entry))
        G.cluster(composite, schedule)
        return composite

    def _make_actor_fsm(actor, fsm_spec, info):
        # create FSM node
        fsm = actor.withNode("_fsm")
        fsm_entry = ty.KernelNode(name="_fsm", _info=info,)
        G.register_child(actor, G.new(fsm, fsm_entry))
        log.info(f"  - Created detector node: {fsm}")

        # connect inputs to FSM
        for port in fsm_spec.inputs:
            inp = actor.withPath(ty.Uid(port))
            assert G.ir.has_node(inp)
            # assert G.entry(inp).dir != ty.Dir.OUT
            cpy = _port_copy(inp.name(), fsm, G.entry(inp))
            G.entry(cpy).dir = ty.Dir.IN
            G.connect(inp, cpy, edge=ty.Edge(ports.Assign,
                      ty.Relation.EVENT, {}, {}), recursive=False)
            log.info(f"  - Connected detector input: {port}")

        # create a new type + new port for FSM states
        if fsm_spec.states is not None:
            qual_name = f"{actor.parent().name()}.{actor.name()}_states"
            type_spec = {"type": "enum", "val": fsm_spec.states}
            port_name = G.entry(actor).name + "_fsm_state"
            state_entry = ty.Port(
                port_name, ty.Dir.INOUT, _info=info, port_type=ports.Assign(),
                data_type={"from_assign": {qual_name: type_spec}},)
            state_port = _port_copy(state_entry.name, fsm, state_entry)
            actor_port = _port_copy(state_entry.name, actor, state_entry)
            G.connect(state_port, actor_port, recursive=False)
            log.info(f"  - Created state variable: {state_port}")

        return fsm

    # for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
    for actor in [n for n in G.ir.nodes if isinstance(G.entry(n), ty.ActorNode)]:
        entry = G.entry(actor)
        if entry.detector is not None:
            # tag preprocessor
            if entry.detector.preproc is not None:
                G.decouple(actor.withNode(entry.detector.preproc))
                ppc_id = actor.withNode(entry.detector.preproc)
                G.entry(ppc_id).mark["preproc"] = True
                log.info(
                    f"  - Found preproc {actor.withNode(entry.detector.preproc)}")
            # tag scenarios
            if entry.detector.scenarios is not None:
                for scen in entry.detector.scenarios:
                    scen_id = actor.withNode(scen)
                    G.entry(scen_id).mark["scenario"] = True
            # create FSM node and mark it with the FSM description for posterity
            fsm = _make_actor_fsm(actor, entry.detector, entry._info)
            G.entry(fsm).mark["detector"] = entry.detector

        # select all untagged nodes under a "default scenario"
        tags = ["preproc", "scenario", "detector"]
        kerns = G.children(actor, select=lambda n: all(
            [t not in n.mark for t in tags]))
        if len(kerns) > 0:
            clus = _cluster_underneath("default", actor, kerns, entry._info,)
            G.entry(clus).mark["scenario"] = True
            log.info(f"  - Created default scenario from {kerns}")

    return True
