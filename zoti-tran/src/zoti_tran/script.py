import pickle
import logging as log
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from zoti_yaml import get_pos
from zoti_graph import AppGraph, Port, Primitive, dump_node_info, draw_graph, draw_tree


@dataclass(eq=False, repr=False)
class TransSpec:
    """Transformation specification wrapper. Extends the transformatiion
    with some control flags and arguments, e.g., useful when
    debugging.

    """

    func: Callable
    """the transformation function"""

    clean: List[str] = field(default_factory=list)
    """list of names of previous transformations, whose byproducts should
    be *completely removed* from the handler's state.

    """

    dump_tree: Optional[Dict] = None
    """keyword-arguments sent to `zoti_graph.io.draw_tree()
        <../zoti-graph/api-reference>`_. If left ``None``, the tree
        structure will not be dumped.

    """

    dump_graph: Optional[Dict] = None
    """keyword-arguments sent to `zoti_graph.io.draw_graph()
        <../zoti-graph/api-reference>`_. If left ``None``, the graph
        structure will not be dumped.

    """

    dump_nodes: bool = False
    """dump node info as text after transformation for debugging"""

    dump_prefix: Optional[str] = None
    """overrides the :class:`Script` member with the same name."""

    dump_title: Optional[str] = None
    """optional title for the dumped file. If left ``None`` it will be
    replaced by the function name.

    """


class Script:
    """Transformation script handler. It storgit ses an application graph and
    (possibly) a data type handler and contains utilities for
    executing rules.

    :param G: a fully-constructed application graph
    :param T: (optional) a data type handler
    :param dump_prefix: path where intermediate results will be written to


    Apart from altering the application graph as side effects,
    transformation rules are able to return byproducts. These
    byproducts are gradually stored and are accessible as class
    members baring the name of the applied rule. E.g., after applying
    a transformation ``TransSpec(foo)`` where::

        def foo(G, **kwargs):
            # do something on G
            return 'bar'

    the current script will have a new member ``foo`` containing the
    string ``'bar'``. Existing members with the same name are
    overriden.

    """

    def __init__(self, G: AppGraph, T=None, dump_prefix="."):
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

    def sanity(self, rules: List[Callable]):
        """Utility for checking a batch of sanity rules on different elements
        of the stored graph (see
        `zoti_graph.appgraph.AppGraph.sanity()
        <../zoti-graph/api-reference>`_) based on their name
        formation:

        * ``port_[name]`` are applied only on ports;
        * ``edge_[name]`` are applied only on edges;
        * ``primitive_[name]`` are applied only on primitives;
        * ``node_[name]`` are applied only on regular nodes;
        * in all other cases it applies the rule on the entire graph
          (i.e., the root node).
        """
        log.info(f"*** Verifying sanity rules for graph {self.G.root}***")

        port_rules = [r for r in rules if r.__name__.startswith("port")]
        node_rules = [r for r in rules if r.__name__.startswith("node")]
        primitive_rules = [
            r for r in rules if r.__name__.startswith("primitive")]
        edge_rules = [r for r in rules if r.__name__.startswith("edge")]
        graph_rules = [r for r in rules if r not in
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
        log.info(
            f"  - passed {[f.__name__ for f in port_rules + primitive_rules + node_rules]}")

        _check(graph_rules, self.G.root)
        log.info(f"  - passed {[f.__name__ for f in graph_rules]}")

    def transform(self, rules: List[TransSpec]):
        """Applies a sequence of graph transformation rules, each wrapped in a
        :class:`TransSpec` container, upon an application graph. Each
        transformation function might generate byproduct results which
        will be stored in the handlers's state (see class
        documentation above).

        Whenever calling a transformation rule, the :class:`Script`
        handler passes its entire state as keyword arguments,
        including the graph and all previous byproducts. This has two
        major implications:

        * any transformation rule should be prepared to be called with
          unknown arguments (by padlocking it with `**kwargs`);
        * data can be passed between transformations as byproducts;
        * dependencies on previous transformations can be specified as
          aguments, e.g.::

              def foo(G, baz, **kwargs):
                  # will fail if rule 'baz' has not been called before
                  # or has not returned anything

        **OBS:** graph alterations are permanent. If you want to store
        intermediate graphs this should be done in the transformation
        function by deep-copying the entire graph and returning it as
        a byproduct.

        """
        log.info(
            f"*** Applying transformation rules for graph {self.G.root}***")

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
                    log.info(
                        f"  ! rule '{rule.func.__name__}' returned {type(ret)}")
                for to_clean in rule.clean:
                    delattr(self, to_clean)
                title = rule.dump_title if rule.dump_title else name
                if rule.dump_graph is not None:
                    with open(prefix.joinpath(f"{title}_graph.dot"), "w") as f:
                        draw_graph(self.G, f, **rule.dump_graph)
                if rule.dump_tree is not None:
                    with open(prefix.joinpath(f"{title}_tree.dot"), "w") as f:
                        draw_tree(self.G, f, **rule.dump_tree)
                if rule.dump_nodes:
                    with open(prefix.joinpath(f"{title}_nodes.txt"), "w") as f:
                        dump_node_info(self.G, f)

            except TypeError as e:
                msg = "Transformation failed. Possibly missing dependency on"
                msg += f"previous transformation byproduct:\n{e}"
                raise ScriptError(msg, rule=rule.func)
            except Exception as e:
                msg = f"Transformation failed:\n{e}"
                raise ScriptError(msg, rule=rule.func)


class ScriptError(Exception):
    """Exception handler for pretty errors, possibly containing positional
    information as provided by `ZOTI-YAML <../zoti-yaml/>`_ and rule
    documentation.

    :param what: error message
    :param obj: object causing the error. Will be scanned for positional info.
    :param rule: the rule (i.e., function itself) where error was caused. Will
      be scanned for docstring.

    """

    def __init__(self, what, obj=None, rule=None):
        self.what = what
        self.pos = f"\n{get_pos(obj).show()}" if get_pos(obj) else ""
        self.name = f" during rule '{rule.__name__}':" if rule else ""
        self.doc = (f"\n\nRule documentation:\n{rule.__doc__}"
                    if getattr(rule, "__doc__", None) else "")

    def __str__(self):
        return f"{self.name}\n{self.what}{self.pos}{self.doc}"


class ContextError(Exception):
    """Exception handler for pretty errors that happened within a context
    of another object, possibly containing positional information as
    provided by `ZOTI-YAML <../zoti-yaml/>`_.

    :param what: error message
    :param obj: object causing the error. Will be scanned for positional info.
    :param context: context message
    :param context_obj: object constituting the context of the error. Will be 
       scanned for positional info.

    """

    def __init__(self, what, obj=None, context="", context_obj=None):
        self.what = what
        self.context = context
        self.pos = f"\n{get_pos(obj).show()}" if get_pos(obj) else ""
        self.ctx_pos = f"\ncontext {get_pos(context_obj).show()}" if get_pos(
            obj) else ""

    def __str__(self):
        return f"{self.context}{self.ctx_pos}\n{self.what}{self.pos}"
