# ZOTI-FTN

ZOTI-FTN (Flexile Type Notation) is an experimental tool for
describing common data types and generating glue code in various
target languages. It consists of:

* a [language](language) for describing a (small) set of data types
  and their properties in a target-agnostic manner. The language comes
  with a parser CLI tool which dumps the ZOTI-FTN AST.

* a [base handler and target-agnostic AST](agnostic) for building modules
  of types and aiding with target-agnsostic tasks, e.g. retrieving
  properites, dependencies, etc.

* (currently only) a [handler instance and derived AST for C
  backends](backend-c) for generating various kind of glue code for
  bare-metal C based on the type properties.

*Note:* This tool is in early experimental phases and might be
deprecated in the future. It is mainly maintained for the sake of
demonstrators, but a more scalable alternative is being
researched. For an overview discussion on the role of ZOTI-FTN and its
position in a synthesis flow such as Genny please refer to the [ZOTI
project hub page](https://ericsson.github.io/zoti/).

The current implementation of ZOTI-FTN is as a Python library. For
installation and usage instructions, please refer to the project's
[GitHub page](https://github.com/Ericsson/zoti/tree/main/zoti-graph).

## Documentation pages

```{toctree}
:maxdepth: 2

language

agnostic

backend-c
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`


