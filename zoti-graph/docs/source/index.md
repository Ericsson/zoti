# ZOTI-Graph

ZOTI-Graph is the core format for system models used between tools in
the [ZOTI project](https://ericsson.github.io/zoti/). Its purpose is
to provide a minimal language to represent hierarchical graph-like
structures, as well as an API to manipulate them or extract
information.

:::{figure} assets/drawing-0.png
Possible drawing of a specific instance of a ZOTI-Graph model.
:::

## Feature Highlights

ZOTI-Graph is for all intents and purposes a hierarchical graph format
built on top of [NetworkX](https://networkx.org/). Its main purpose is
to represent systems descriptions by annnotating its elements or by
means of class inheritance and specialization. ZOTI-Graph models are
intended to be used in the development of [synthesis
flows](https://ericsson.github.io/zoti/), hence the ZOTI-Graph tool
features:

- a [generic API](api-reference) for parsing, extracting information
  and altering the structure of ZOTI-graphs. The API also exposes the
  internal [NetworkX](https://networkx.org/) structure such that
  generic graph algorithms can be applied on ZOTI-graphs.
  
- a [script handler](script) with utilities for setting up
  transformation flows on ZOTI-graphs.

- (at the moment only) an [specialized instance](genny) of the
  ZOTI-graph format to be used with the [Genny synthesis
  flow](https://ericsson.github.io/zoti/), which represents system
  application views as graphs of concurrent actors. This format comes
  together with a parser, a set of sanity rules and a set of
  target-agnostic transformations compatible with the script handler.

For an overview discussion on the role of ZOTI-Graph and its position
in a synthesis flow such as Genny please refer to the [ZOTI project
hub page](https://ericsson.github.io/zoti/).

The current implementation of ZOTI-Graph is as a Python library using
mainly [NetworkX](https://networkx.org/) for internal structure
representation. For a feature list as well as installation and usage
instructions, please refer to the project's [GitHub
page](https://github.com/Ericsson/zoti/tree/main/zoti-graph).

## Documentation pages

```{toctree}
:maxdepth: 2

genny

api-reference

script

tutorial
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`


