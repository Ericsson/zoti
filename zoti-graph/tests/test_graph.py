import zoti_graph.io as io
from zoti_graph.parser import parse
from zoti_graph.core import Uid, Dir, Primitive, CompositeNode
import os
import sys
import yaml
import logging as log
from pprint import pprint
from pathlib import PurePosixPath

sys.path.insert(0, "src")


def test_scenario1() -> None:

    with open("tests/inputs/graph1.yaml") as f:
        G = parse(*yaml.load_all(f, Loader=yaml.Loader))
    print("")

    assert G.depth(
        Uid("Tst/Src/counter/buffer-flush/_kern/^flush_cnt")
    ) == 5
    assert G.entry(
        Uid("Tst/Src/counter/buffer-flush/^flush_cnt"),
        Uid("Tst/Src/counter/buffer-flush/_kern/^flush_cnt")
    ) is not None
    assert G.get_mark(
        "probe_buffer",
        Uid("Tst/Src/counter/buffer-flush/_kern/^cnt_buff"),
    ) is True
    assert G.entry(
        Uid("Tst/Src/counter/buffer-flush/_kern/^cnt_buff")
    ).dir == Dir.INOUT
    assert len(G.children(
        Uid("Tst"),
        select=lambda x: not isinstance(x, Primitive)
    )) == 2

    # TODO: removed from API. retest if needed
    # pprint(G.out_edges(Uid("Tst/Src/counter")))
    # assert len(G.out_edges(
    #     Uid("Tst/Src/counter")
    # )) == 5
    # assert len(G.in_edges(
    #     Uid("Tst/Src/counter")
    # )) == 4

    assert len(list(G.connected_ports(
        Uid("Tst/Src/counter/^monitored_input")
    ).nodes)) == 10
    assert len(G.end_ports(
        Uid("Tst/Src/counter/^monitored_input")
    )) == 3
    assert G.is_leaf(Uid("Tst/Src/counter")) == False
    assert G.is_leaf(Uid("Tst/Src/counter/buffer-flush/_kern")) == True
    assert G.has_ancestor(
        Uid("Tst/Src/counter/buffer-flush/_kern"),
        Uid("Tst/Src")
    )

    #### ALTERATIONS ####
    G.new(Uid("Tst/clust"), CompositeNode("testclus", {}, {}))
    G.register_child(Uid("Tst"), Uid("Tst/clust"))
    G.cluster(Uid("Tst/clust"), [Uid("Tst/Src"), Uid("Tst/streamq")])

    assert G.ir.has_node(Uid("Tst/clust/^flush"))
    assert G.ir.has_edge(Uid("Tst/sys2"), Uid("Tst/clust/^flush"))
    assert G.ir.has_edge(Uid("Tst/Src/^data"), Uid("Tst/streamq/^ldata"))

    G.uncluster(Uid("Tst/clust"))
    assert G.ir.has_node(Uid("Tst/clust/^flush")) == False
    assert G.ir.has_edge(Uid("Tst/sys2"), Uid("Tst/Src/^flush"))
    assert G.ir.has_edge(Uid("Tst/Src/^data"), Uid("Tst/streamq/^ldata"))

    assert len(G.node_projection(Uid("Tst/Src/counter")).nodes()) == 3
    assert len(G.node_projection(
        Uid("Tst/Src/counter"), with_parent=False)) == 2

    G.bypass_port(Uid("Tst/Src/counter/buffer-flush/^cnt_buff"))
    # io.draw_graph(G, "graph.dot")
    try:
        G.entry(
            Uid("Tst/Src/counter/buffer-flush/^cnt_buff"),
            Uid("Tst/Src/counter/buffer-flush/_kern/^cnt_buff")
        )
        assert False
    except Exception:
        pass
    assert G.entry(
        Uid("Tst/Src/counter/packet-cnt/^cnt_buff"),
        Uid("Tst/Src/counter/buffer-flush/_kern/^cnt_buff")
    ) is not None

    # dump.draw_tree(G, "tree.dot")
    G.fuse_nodes(
        Uid("Tst/streamq/release_data"),
        Uid("Tst/streamq/queue_data")
    )
    assert (G.parent(Uid("Tst/streamq/release_data/strq_fetch_blk"))
            == G.parent(Uid("Tst/streamq/queue_data/streamq_lnk_act")))

    try:
        with open("tmp.dot", "w") as f:
            io.draw_graph(G, f)
            io.draw_tree(G, f)
        with open("tmp.yaml", "w") as f:
            yaml.dump_all(
                [list(G.ir.nodes(data=True)), list(G.ir.edges(data=True))], f, Dumper=io.AppGraphDumper, default_flow_style=None,)
        with open("tmp.yaml") as f:
            G.reset(G.root)
            raw = list(yaml.load_all(f, Loader=io.AppGraphLoader))
            G.ir.add_nodes_from(raw[0])
            G.ir.add_edges_from(raw[1])
            assert G.depth(
                Uid("Tst/Src/counter/buffer-flush/_kern/^flush_cnt")
            ) == 5
    except Exception as e:
        raise e
    finally:
        os.remove("tmp.dot")
        os.remove("tmp.yaml")
