# Genny-Graph

Genny-Graph is the instance of ZOTI-Graph used with the
[Genny](https://ericsson.github.io/zoti/) syntesis flow of the ZOTI
project. As a model it represents applications as graphs of concurrent
actors where nodes are hierarchically representing compute components
and their mapping whereas each edge represents a type of interaction
between the compute components.
  
As part of the Genny flow, Genny-Graph aims to act as a bridge between
(completely solved) system models and their pragmatic implementation
on a given (heterogeneous) target platform. In this sense it imposes
enough restrictions on the design as to enable hosting behavior
semantics as well as it allows custom annotations and "hacks" for
aiding towards more efficient implementations. In other words its goal
is to enable the use of (upstream) formal models without necesserily
crippling the possibility of (downstream) efficient code generation.

To achieve hierarchy each node is considered as being connected to its
surroundings via ports, effectively being able to be abstracted as a
"black-box" component. By adopting this view a node can be itself
cluster of interconnected nodes, as suggested in the figure below.

:::{figure} assets/splash.png
Drawing of a Genny-graph model
:::

There is enough consistency between the input format schema and the
model specification hence we will use the former to document both
model and input format.

Notice that there are several types of nodes, as documented in the
[](#nodes) section below. These nodes cannot be arranged in any
arbitrary hierarchy, and there are a set of rules that need to be
enforced when describing system models, as described in the
[](#sanity-rules) section below. Finally, a set of
[](#target-agnostic-transformations) are exported and can be used as
reference to create own ones.

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
.. autosimple:: zoti_graph.genny.parser.NodeParser
```

#### Node Kinds

There are several types of nodes, each one denoting a specific part of
a system. Depending on type, additional fields can be used to
described specific information, as documented below.

##### CompositeNode

```{eval-rst}
.. autosimple:: zoti_graph.genny.parser.CompositeNodeParser

```

##### PlatformNode

```{eval-rst}
.. autosimple:: zoti_graph.genny.parser.PlatformNodeParser
```

##### ActorNode

```{eval-rst}
.. autosimple:: zoti_graph.genny.parser.ActorNodeParser
```

##### KernelNode

```{eval-rst}
.. autosimple:: zoti_graph.genny.parser.KernelNodeParser
```

##### BasicNode

```{eval-rst}
.. autosimple:: zoti_graph.genny.parser.BasicNodeParser

```

### ports

```{eval-rst}
.. autosimple:: zoti_graph.genny.parser.PortParser
```

### edges

```{eval-rst}
.. autosimple:: zoti_graph.genny.parser.EdgeParser

```

## Model Parser

The previous schema can describe a serialization format (e.g. JSON or
YAML) that is parsed and validated using the following method exported
by {mod}`zoti_graph.genny`.


```{eval-rst}
.. autofunction:: zoti_graph.genny.parser.parse
```

## Sanity rules

After parsing and creating an application graph, a set of sanity rules
need to be enforced. Genny-Graph comes with a set of generic callable
assertion functions (using the
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

> The following sanity rules are currently defined by
> Genny-Graph. They are not re-exported by the Genny main module, so
> they need to be imported explicitly from
> {mod}`zoti_graph.genny.sanity`.

```{eval-rst}
.. automodule:: zoti_graph.genny.sanity
	:members:

```
## Target-Agnostic Transformations

> These functions need to be explicitly imported from
> {mod}`zoti_graph.genny.translib`.


```{eval-rst}
.. automodule:: zoti_graph.genny.translib
	:members:
```

## Core Container Types

Each graph element in a Genny-Graph is associated with a container
entry used for storing information that can be used during various
stages of model transformations.

> These classes are re-exported by {mod}`zoti_graph.genny.translib`

```{eval-rst}
.. automodule:: zoti_graph.genny.core
	:members:
	:undoc-members:
	:show-inheritance:
```
