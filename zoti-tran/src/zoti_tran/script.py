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

    def sanity(self, rules=[]):
        """Applies sanity checks for a list of *rules* (see
        :ref:`AppGraph.sanity`). This method groups rules based on
        their function name:
        
        - if the rule name starts with 'port' it will be applied only on ports
        
        - if the rule name starts with 'edge' it will be applied only
          on edges

        - if the rule name starts with 'primitive' it will be applied
          only on primitives

        - if the rule name starts with 'node' it will be applied only
          on regular nodes (not primitives)

        - in all other cases it applies the rule on the entire graph
          (i.e., the root node)

        """
        log.info(f"*** Verifying sanity rules for graph {self.G.root}***")

        port_rules=[r for r in rules if r.__name__.startswith("port") ]
        node_rules=[r for r in rules if r.__name__.startswith("node") ]
        primitive_rules=[r for r in rules if r.__name__.startswith("primitive") ]
        edge_rules=[r for r in rules if r.__name__.startswith("edge") ]
        graph_rules=[r for r in rules if r not in
                     port_rules + node_rules + primitive_rules + edge_rules]

        def _check(collection, *element):
            for rule in collection:
                self.G.sanity(rule, *element)

        for edge in self.G.only_graph().edges:
            _check(edge_rules, *edge)
        log.info(f"  - passed {[f.__name__ for f in edge_rules]}")

        for node in self.G.ir.nodes:
            if isinstance(self.G.entry(node), Port):
                _check(port_rules, node,)
            elif isinstance(self.G.entry(node), Primitive):
                _check(primitive_rules, node)
            else:
                _check(node_rules, node)
        log.info(f"  - passed {[f.__name__ for f in port_rules + primitive_rules + node_rules]}")

        _check(graph_rules, self.G.root)
        log.info(f"  - passed {[f.__name__ for f in graph_rules]}")
            

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

