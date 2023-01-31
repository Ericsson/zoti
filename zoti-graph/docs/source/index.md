# ZOTI-Graph

ZOTI-Graph is the core format for system models used in the [ZOTI
project](TODO). Its purpose is to provide a minimal language to
represent system models with the sole purpose of generating code, as
well as tools to manipulate this representation during a (scripted)
code synthesis flow.

:::{figure} assets/splash.png
(possible drawing of a ZOTI-Graph model [^id2])
:::

The main highlights of the ZOTI-Graph representation are:

> - it aims to provide a simple, generic, target-agnostic and
>   language-independent format to describe application models as well
>   as their implementation details in a declarative, parser-friendly
>   manner.
> - it aims to act as a bridge between (possibly formal) system models
>   and their pragmatic implementation on a given (heterogeneous)
>   target platform. In this sense it imposes enough restrictions on
>   the design as to enable hosting behavior semantics as well as it
>   allows custom annotations and "hacks" for aiding towards more
>   efficient implementations. In other words its goal is to enable the
>   use of (upstream) formal models without necesserily crippling the
>   possibility of (downstream) efficient code generation.
> - it represents applications as graphs of concurrent actors where
>   nodes are hierarchically representing compute components and their
>   mapping whereas each edge represents a type of interaction between
>   the compute components.

For an overview discussion on the role of ZOTI-Graph and its position
in a synthesis flow please refer to the [ZOTI project hub page](TODO).

The current implementation of ZOTI-Graph is as a Python library using
mainly [NetworkX](https://networkx.org/) for internal structure
representation. For a feature list as well as installation and usage
instructions, please refer to the project's [GitHub page](TODO).

## Documentation pages

```{toctree}
:maxdepth: 2

the-zoti-graph-model

api-reference
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`

[^id2]: The format is still in development and there might be
    discrepancies between drawings and definition. For proper
    definitions check the [Model Documentation](the-zoti-graph-model) page.
