# ZOTI-Tran

ZOTI-Tran(sformations) is a simple skeleton project to help getting
started with building an own transformation-based code synthesis flow
following the [ZOTI](https://ericsson.github.io/zoti) methodology. It
contains some function drivers that may (or may not) be used when
describing transformation scripts, as well as a small set of generic
(i.e., platform-agnostic)
[ZOTI-Graph](https://ericsson.github.io/zoti/zoti-graph)
transformations.

Functionally, ZOTI-Tran can be considered an extension of
[ZOTI-Graph](https://ericsson.github.io/zoti/zoti-graph), defining
procedures to manipulate the internal structure of an application
graph based on its specification and its target. Since currently
ZOTI-Graph is written in Python, it naturally follows that a
full-scale ZOTI-Tran tool would also be written in Python and make use
of the graph API. No other obvious inter-dependency is present by
design, other tools being able to share their information via
serialization formats.

## Documentation pages

```{toctree}
:maxdepth: 2

api-reference
```


## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
