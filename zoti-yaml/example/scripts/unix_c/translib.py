from copy import deepcopy
import networkx as nx
import logging as log
import zoti_graph as ty
import zoti_graph.util as util

import ports


def port_inference(G, T, **kwargs):
    """Resolves and fills in the *data_type* and the *port_type* fields
    for all groups of interconnected ports. Port resolution is defined
    in :module:`zoti_tran.unix_c.ports`. After this transformation the
    following holds:

    forall p in ports(G)
      | p.data_type ∈ zoti_ftn.backend.c
      | p.port_type ∈ zoti_tran.unix_c.ports

    """
    ag = G.only_graph().to_undirected()
    for conn in list(nx.connected_components(ag)):
        pids = [p for p in conn if isinstance(G.entry(p), ty.Port)]
        pents = [G.entry(p) for p in pids]
        if not pids:
            continue
        port_type = ports.make_port_type(pents, pids)
        data_type = ports.make_data_type(pents, T, pids)
        orig_mark = ports.make_markings(pents, pids)
        for p in pids:
            G.entry(p).port_type = port_type
            G.entry(p).data_type = data_type
            G.entry(p).mark = orig_mark
        log.info(f"  - Resolved {pids}")

    return True  # Byproduct is a flag


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
            G.connect(inp, cpy, edge=ty.Edge(ports.Assign, ty.Relation.EVENT, {}, {}), recursive=False)
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
                G.add_mark("preproc", True, actor.withNode(entry.detector.preproc))
                log.info(f"  - Found preproc {actor.withNode(entry.detector.preproc)}")
            # tag scenarios
            if entry.detector.scenarios is not None:
                for scen in entry.detector.scenarios:
                    G.add_mark("scenario", True, actor.withNode(scen))
            # create FSM node and mark it with the FSM description for posterity
            fsm = _make_actor_fsm(actor, entry.detector, entry._info)
            G.add_mark("detector", entry.detector, fsm)

        # select all untagged nodes under a "default scenario"
        tags = ["preproc", "scenario", "detector"]
        kerns = G.children(actor, select=lambda n: all([t not in n.mark for t in tags]))
        if len(kerns) > 0:
            clus = _cluster_underneath("default", actor, kerns, entry._info,)
            G.add_mark("scenario", True, clus)
            log.info(f"  - Created default scenario from {kerns}")

    return True

def clean_ports(G, port_inference, **kwargs):
    """This transformation performs the following: 

      * removes all conections to/from NULL;
      * pomotes STORAGE ports to platform level (will become global variables)
      * marks multi-input ports for creating buffers, and promotes them to platform level
      * removes intermediate STORAGE ports. Only end connections + global remain
      * removes nodes marked as "ignore" (e.g., hook nodes)
      * identifies/creates and marks ports which will become intermediate variables

    """
    def _make_global(pltf, name, port) -> str:
        glb_key = util.unique_name(pltf.withPort(name), G.ports(pltf),
                                   modifier=lambda u, s: u.withSuffix(s))
        newport = deepcopy(port)
        newport.name = f"_{pltf.name()}_{glb_key.name()}".replace(".", "_")
        G.register_port(pltf, G.new(glb_key, newport))
        G.add_mark("global_var", True, glb_key)
        return newport.name

    def _remove_selected_ports(connected, select):
        to_remove = [p for p in connected.nodes() if select(p)]
        for p in to_remove:
            G.ir.remove_node(p)
        return to_remove

    def _new_intermediate_connection(src, dst, parent):
        edge = G.entry(src, dst)
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
            G.add_mark("inter_var", True, inter)
            pentry.dir = ty.Dir.INOUT
            for new_src in [u for u, v in G.port_edges(dst, out=False)]:
                G.connect(new_src, inter, edge, recursive=False)
        G.ir.remove_edge(src, dst)
        G.connect(inter, dst, edge, recursive=False)
        return inter

    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        for actor in G.children(pltf, select=lambda n: isinstance(n, ty.ActorNode)):
            for port in G.ports(actor):
                conn = G.connected_ports(port)
                ends = G.end_ports(port, graph=conn)
                entry = G.entry(port)
                
                # sync names of interconneted storage ports and make globals for them
                if (G.entry(*G.port_edges(port)[0]).kind == ty.Relation.STORAGE
                    and not G.get_mark("global_var", port)):
                    glb_name = _make_global(pltf, entry.name, entry)
                    for p in [e for e in ends if isinstance(G.entry(e), ty.Port)]:
                        G.entry(p).name = glb_name
                        G.add_mark("global_var", True, p)
                    log.info(f"  - Promoted to global '{glb_name}': {conn.nodes}")

                # # change type of input ports to reflect their mechanism
                # if entry.dir == ty.Dir.IN:
                #     G.decouple_entry(port)
                #     entry = G.entry(port)
                #     entry.data_type = entry.port_type.get_port_type()
                
                # remove all actor ports connected to NULL (and the NULL connections)
                nulls = [snk for snk in ends
                         if isinstance(G.entry(snk), ty.Primitive)
                         and G.entry(snk).is_type(ty.PrimitiveTy.NULL)]
                if nulls:
                    def _to_remove(p):
                        is_outside = not G.has_ancestor(p, G.parent(port))
                        is_intermediate = conn.degree(p) > 1
                        return is_outside or is_intermediate
                    rmd = _remove_selected_ports(conn, _to_remove)
                    log.info(f"  - Removed dangling ports {rmd}")

                # remove all intermediate storage connections
                elif G.entry (*G.port_edges(port)[0]).kind == ty.Relation.STORAGE:
                    # G.depth(p) <= G.depth(port)
                    def _to_remove(p):
                        return conn.degree(p) > 1
                    rmd = _remove_selected_ports(conn, _to_remove)
                    log.info(f"  - Removed intermediate storage ports {rmd}")

            for scen in G.children(actor,
                                   select=lambda n: isinstance(n, ty.CompositeNode)):

                #remove ignore nodes and downstream ports propagated
                for node in G.children(scen, select=lambda n: "ignore" in n.mark):
                    dsts = G.ports(node)
                    while dsts:
                        tmp = []
                        for p in dsts:
                            conns = G.bypass_port(p)
                            tmp.extend([v for u, v in conns
                                        if G.depth(v) <= G.depth(node)])
                        dsts = tmp
                    G.ir.remove_node(node)
                
                # expose intermediate variables in scenarios
                proj = G.node_projection(scen, with_parent=False)
                for src_kern, dst_kern in proj.edges():
                    for src, dst in proj[src_kern][dst_kern]["ports"]:
                        inter = _new_intermediate_connection(src, dst, scen)
                        log.info(f"  - Using {inter} as intemediate between ({src}, {dst})")

                # add forced dependency to "probe_counter" nodes
                for node in G.children(scen, select=lambda n: "probe_counter" in n.mark):
                    for ups, _ in G.node_edges(node, in_outside=True):
                        for down in [v for u, v in G.port_edges(ups, inp=False, out=True)
                                        if G.parent(v) != node]:
                            entry=deepcopy(G.entry(ups))
                            entry.dir = ty.Dir.OUT
                            dummy = G.register_port(node, G.new(
                                node.withPort("_dummy"), entry))
                            G.connect(dummy, down, G.entry(ups, down), recursive=False)

                # # marking timer input as global; HACK, to enable writing to it
                # for node in G.children(scen):
                #     for port in G.ports(node, select=lambda p: isinstance(p.port_type, ports.Timer)):
                #         G.decouple(port)
                #         entry = G.entry(port)
                #         entry.mark["global_var"] = True
                

        # alter exit ports to reflect socket variables
        for oport in G.ports(
            pltf,
            select=lambda p: p.dir == ty.Dir.OUT
            and isinstance(p.port_type, ports.Socket),  # TODO
        ):
            G.decouple(oport)
            entry = G.entry(oport)
            entry.name = f"{pltf.name()}_{entry.name}_ram2udp_socket"
            entry.data_type = {"usage": "int", "value": "0"}
            entry.mark["global_var"] = True
            entry.mark["socket"] = True
    return True

def separate_reactions(G, clean_ports, **kwargs):
    def _make_global(pltf, name, port) -> str:
        glb_key = util.unique_name(pltf.withPort(name), G.ports(pltf),
                                   modifier=lambda u, s: u.withSuffix(s))
        newport = deepcopy(port)
        newport.name = f"_{pltf.name()}_{glb_key.name()}".replace(".", "_")
        G.register_port(pltf, G.new(glb_key, newport))
        G.add_mark("global_var", True, glb_key)
        return newport.name
    
    def _duplicate_scenario(port, scen):
        new = G.copy_tree(scen, f"A_{port.name()}_A")
        iports = G.ports(new, select=lambda p: p.dir == ty.Dir.IN)
        # G.ir.remove_nodes_from([p for p in iports if p.name() != port.name()])
        for p in iports:
            if p.name() != port.name():
                for ep in G.end_ports(p):
                    G.decouple(ep)
                    G.add_mark("global_var", True, ep)
                G.ir.remove_node(p)
        for u, v in G.node_edges(scen, in_outside=True):
            for iport in G.ports(new):
                if v.name() == iport.name():
                    G.connect(u, iport, G.entry(u, v), recursive=False)
        for u, v in G.node_edges(scen, out_outside=True):
            for oport in G.ports(new):
                if u.name() == oport.name():
                    G.connect(oport, v, G.entry(u, v), recursive=False)
    
    for pltf in G.children(G.root, select=lambda n: isinstance(n, ty.PlatformNode)):
        for actor in G.children(pltf, select=lambda n: isinstance(n, ty.ActorNode)):
            for scen in G.children(actor, select=lambda n: "scenario" in n.mark):
                iports = [(p, q)
                          for p in G.ports(actor, select=lambda p: p.dir == ty.Dir.IN)
                          for q in G.connected_ports(p) if G.parent(q) == actor]
                if len(iports) > 1:
                    for scenp, actorp in iports:
                        name = _make_global(pltf, scenp.name(), G.entry(scenp))
                        G.decouple(actorp)
                        G.add_mark("buff_name", name, actorp)
