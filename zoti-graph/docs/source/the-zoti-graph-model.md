# Model Documentation

The ZOTI-Graph model is an internal representation of system-level
applications as hierarchical graphs of nodes representing
computations, and edges representing the relations between these
computations.

To achieve hierarchy each node is considered as being connected to its
surroundings via ports, effectively being able to be abstracted as a
"black-box" component. By adopting this view a node can be itself
cluster of interconnected nodes, as suggested in the figure below.

:::{figure} assets/splash.png
:::

There is enough consistency between the input format schema and the
model specification hence we will use the former to document both
model and input format.

Notice that there are several types of nodes, as documented in the
[](#nodes) section below. These nodes cannot be arranged in any
arbitrary hierarchy, and there are a set of rules that need to be
enforced when describing system models, as described in the
[](#sanity-rules) section below.

## Input Schema

ZOTI-Graphs documents are specified as hierarchical tree-like objects
where the root is a [](#nodes) field containing a list of definitions
representing the top-level node(s). From there systems are described
in a top-down manner where child nodes are specified within the scope
of parent nodes (i.e. under the parent's [](#nodes) field).

A graph is loaded from a list of serialized objects (e.g. in JSON
format) using the {meth}`zoti_graph.parser.parse` method, by passing
them to its arguments. The *document* object from these arguments
needs to be defined following the schema below.

### nodes

```{eval-rst}
.. autosimple:: zoti_graph.parser.NodeParser
```

#### Node Kinds

There are several types of nodes, each one denoting a specific part of
a system. Depending on type, additional fields can be used to
described specific information, as documented below.

##### CompositeNode

```{eval-rst}
.. autosimple:: zoti_graph.parser.CompositeNodeParser

```

##### PlatformNode

```{eval-rst}
.. autosimple:: zoti_graph.parser.PlatformNodeParser
```

##### ActorNode

```{eval-rst}
.. autosimple:: zoti_graph.parser.ActorNodeParser
```

##### KernelNode

```{eval-rst}
.. autosimple:: zoti_graph.parser.KernelNodeParser
```

##### BasicNode

```{eval-rst}
.. autosimple:: zoti_graph.parser.BasicNodeParser

```

### ports

```{eval-rst}
.. autosimple:: zoti_graph.parser.PortParser
```

### edges

```{eval-rst}
.. autosimple:: zoti_graph.parser.EdgeParser

```

## Sanity rules

After parsing and creating an application graph, a set of sanity rules
need to be enforced. ZOTI-Graph comes with a set of generic callable
assertion-like functions (using the
{meth}`zoti_graph.appgraph.AppGraph.sanity` driver). Depending on the
use case or on the target platform additional sanity rules might need
to be defined and enforced, or skipped, this is why it is up to the
synthesis flow designer to call these rules individually. In general
it is worth noting that:

- the top node of a project is a `CompositeNode` and all its
  children need to be `PlatformNode`. This means that no function
  nor behavior is left "dangling" without being mapped to a specific
  execution platform.
- similar to the previous rule, it makes no sense to speak of a
  "function" outside the scope of a "behavior". In other words any
  `KernelNode` needs to (eventually) be part of an `ActorNode`
  which determines the context in which and the mechanisms with which
  a certain (native) function is being executed."

Following is a list of all sanity rules currently defined by
ZOTI-Graph. They are not re-exported globally, so they need to be
imported explicitly from {mod}`zoti_graph.sanity`.

```{eval-rst}
.. automodule:: zoti_graph.sanity
	:members:

```
