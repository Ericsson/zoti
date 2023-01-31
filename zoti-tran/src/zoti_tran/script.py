import pickle
import logging as log
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from zoti_yaml import get_pos
from zoti_ftn import FtnDb
from zoti_graph import AppGraph, Port, Primitive, dump_node_info, draw_graph, draw_tree


@dataclass(eq=False, repr=False)
class TransSpec:
    """Transformation specification container. Wraps a transformation
    function *func* with run-time flags and arguments.

    """

    func: Callable
    """the transformation function"""

    clean: List[str] = field(default_factory=list)
    """list of previous transformations byproducts which should be cleand
    from the handler's state"""

    dump_tree: Optional[Dict] = None
    """ keyword-arguments sent to :meth:`zoti_graph.appgraph.ZotiAG.draw_tree` """

    dump_graph: Optional[Dict] = None
    """ keyword-arguments sent to :meth:`zoti_graph.appgraph.ZotiAG.draw_graph` """

    dump_nodes: bool = False
    """dump node info after transformation for debugging"""

    dump_prefix: str = None
    """path where the intermediate files will be dumped"""


class Script:
    def __init__(self, G: AppGraph, T: FtnDb = None, dump_prefix="."):
        self._dump_prefix = dump_prefix
        self.G = G
        self.T = T

    @classmethod
    def from_pickle(cls, path):
        """Loads a binary object containing a previously pickled script handler."""
        with open(path, "rb") as f:
            loaded = pickle.load(f)
            assert hasattr(loaded, "G")
            assert hasattr(loaded, "T")
            return loaded

    def pickle(self, path):
        """Dumps the current state of the handler into a binary object."""
        with open(path, "wb") as f:
            pickle.dump(self, f)

    def sanity(
        self,
        port_rules=[],
        node_rules=[],
        primitive_rules=[],
        edge_rules=[],
        graph_rules=[],
    ):
        """Performs sanity checking on various elements in a ZOTI application
        graph by applying the rules provided as arguments. Each
        argument is an iterable containing assertions on the
        respective AppGraph element.

        """
        log.info(f"*** Verifying sanity rules for graph {self.G.root}***")

        def _check(collection, element, obj):
            for rule in collection:
                try:
                    rule(element, self.G)
                except AssertionError:
                    msg = f"Sanity check failed for {element}"
                    raise ScriptError(msg, obj=obj, rule=rule)

        for edge in self.G.only_graph().edges:
            _check(edge_rules, edge, self.G.entry(*edge))
        log.info(f"  - edges passed {[f.__name__ for f in edge_rules]}")

        for node in self.G.ir.nodes:
            if isinstance(self.G.entry(node), Port):
                _check(port_rules, node, self.G.entry(node))
            elif isinstance(self.G.entry(node), Primitive):
                _check(primitive_rules, node, self.G.entry(node))
            else:
                _check(node_rules, node, self.G.entry(node))
        log.info(f"  - nodes passed {[f.__name__ for rule in [port_rules, primitive_rules, node_rules] for f in rule]}")

        _check(graph_rules, self.G, None)
        log.info(f"  - graph passed {[f.__name__ for f in graph_rules]}")

    def transform(self, rules: List[TransSpec]):
        """Applies a sequence of graph transformation rules upon an
        application graph. Each transformation function might generate
        byproduct results which will be stored in the handlers's state
        and passed to all subsequent transformations in the chain,
        unless explicitly removed using the :attr:`TransSpec.clean`
        attribute.

        **OBS:** graph alterations are permanent. If you want to store
        intermediate graphs this should be done in the transformation
        function by deep-copying the entire graph and returning it as
        a byproduct.

        """
        log.info(f"*** Applying transformation rules for graph {self.G.root}***")
        
        for rule in rules:
            try:
                log.info(f" ** applying rule '{rule.func.__name__}'")
                name = rule.func.__name__
                prefix = Path(
                    rule.dump_prefix if rule.dump_prefix else (
                        self._dump_prefix if self._dump_prefix else "."
                    ))
                ret = rule.func(**vars(self))
                if ret is not None:
                    setattr(self, name, ret)
                    log.info(f"  ! rule '{rule.func.__name__}' returned {type(ret)}")
                for to_clean in rule.clean:
                    delattr(self, to_clean)
                if rule.dump_graph is not None:
                    with open(prefix.joinpath(f"graph_{name}.dot"), "w") as f:
                        draw_graph(self.G, f, **rule.dump_graph)
                if rule.dump_tree is not None:
                    with open(prefix.joinpath(f"tree_{name}.dot"), "w") as f:
                        draw_tree(self.G, f, **rule.dump_tree)
                if rule.dump_nodes:
                    with open(prefix.joinpath(f"nodes_{name}.txt"), "w") as f:
                        dump_node_info(self.G, f)

            except TypeError as e:
                msg = "Transformation failed. Possibly missing dependency on"
                msg += f"previous transformation byproduct:\n{e}"
                raise ScriptError(msg, rule=rule.func)
            except Exception as e:
                msg = f"Transformation failed:\n{e}"
                raise ScriptError(msg, rule=rule.func)


class ScriptError(Exception):
    def __init__(self, what, obj=None, rule=None):
        self.what = what
        self.pos = f"\n{get_pos(obj).show()}" if get_pos(obj) else ""
        self.name = f" during rule '{rule.__name__}':" if rule else ""
        self.doc = (f"\n\nRule documentation:\n{rule.__doc__}"
                    if getattr(rule, "__doc__", None) else "")

    def __str__(self):
        return f"{self.name}\n{self.what}{self.pos}{self.doc}"

class ContextError(Exception):
    def __init__(self, what, obj=None, context="", context_obj=None):
        self.what = what
        self.context = context
        self.pos = f"\n{get_pos(obj).show()}" if get_pos(obj) else ""
        self.ctx_pos = f"\ncontext {get_pos(context_obj).show()}" if get_pos(obj) else ""

    def __str__(self):
        return f"{self.context}{self.ctx_pos}\n{self.what}{self.pos}"


# ###############################################################

# if __name__ == "__main__":
#     import os

#     # from pprint import pprint
#     import yaml

#     # import networkx as nx
#     import zoti_tran.agnostic.translib as trans
#     import zoti_tran.unix_c.genspec as genspec
#     import zoti_tran.unix_c.m2m as c
#     from zoti_ftn.backend.c import FtnDb
#     from zoti_ftn.frontend import FtnLoader
#     from zoti_graph import load, parse

#     os.environ["ZOTI_PATH"] = "test"
#     pre, doc = load(Path("test/ScheduledCompute.yaml"))
#     AG = parse(pre, doc)
#     AG.draw_tree("test/tree.dot")
#     AG.draw_graph("test/graph.dot",
#                   port_info=lambda p: str(p.data_type.get("name")))
#     AG.dump_node_info("test/nodes.txt")
#     FTN = FtnDb(search_paths=["test/types"], loader=FtnLoader())

#     handler = Script(AG, FTN)
#     handler.sanity(
#         port_rules=[
#             rules.port_dangling_port,
#         ],
#         node_rules=[
#             rules.node_platform_hierarchy,
#             rules.node_actor_hierarchy,
#             rules.node_actor_consistency,
#             rules.node_kernel_hierarchy,
#         ],
#         edge_rules=[
#             rules.edge_direction,
#             rules.edge_hierarchy,
#             rules.edge_sibling_kind,
#         ],
#     )
#     handler.transform(
#         [
#             TransSpec(
#                 c.port_inference,
#                 dump_graph=True,
#                 dump_graph_args={
#                     "port_info": lambda p: p.port_type.__class__.__name__,
#                     "edge_info": lambda e: str(e.kind),
#                     "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
#                 },
#                 dump_prefix="test",
#             ),
#             TransSpec(
#                 trans.flatten,
#                 dump_tree=True,
#                 dump_graph=True,
#                 dump_nodes=True,
#                 dump_prefix="test",
#             ),
#             TransSpec(
#                 trans.auto_fuse_actors,
#                 dump_tree=True,
#                 dump_graph=True,
#                 dump_nodes=True,
#                 dump_graph_args={
#                     "edge_info": lambda e: str(e.kind),
#                 },
#                 dump_prefix="test",
#             ),
#             TransSpec(
#                 c.expand_actors,
#                 dump_tree=True,
#                 dump_graph=True,
#                 dump_graph_args={
#                     "composite_info": lambda c: str(c.mark),
#                     "port_info": lambda p: ",".join([k for k in p.mark.keys()]),
#                 },
#                 dump_prefix="test",
#             ),
#             TransSpec(
#                 c.clean_ports,
#                 dump_graph=True,
#                 dump_graph_args={
#                     "composite_info": lambda c: str(c.mark),
#                     "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
#                     # "port_info": lambda p: ",".join([k for k in p.mark.keys()]),
#                     # "port_info": lambda p: p.port_type.__class__.__name__,
#                     "port_info": lambda p: p.data_type.__class__.__name__,
#                 },
#                 dump_prefix="test",
#             ),
#             TransSpec(genspec.genspec),
#         ]
#     )

#     typedefs, specs = handler._state["genspec"]
#     for fname, ftext in typedefs.items():
#         with open(f"test/gen/{fname}", "w") as f:
#             f.write(ftext)
#             f.write("\n")

#     for main, spec in specs.items():
#         with open(f"test/gen/genspec.{main}.yaml", "w") as f:
#             f.write(yaml.dump_all(spec, Dumper=genspec.SpecDumper,
#                                   sort_keys=False,
#                                   default_flow_style=False,), )
