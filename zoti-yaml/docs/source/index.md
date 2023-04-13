# ZOTI-YAML

ZOTI-YAML is a YAML language extension that supports describing
document trees distributed across several modules. It consists of:

- special keywords (e.g., `!ref`, `!attach`, `!include`, `!default`)
  that help constructing document trees with information spread across
  several files;
- a module system, i.e. a document preamble structure and a custom
  loader;
- a CLI tool to convert ZOTI-YAML modules to regular YAML or JSON
  files;
- an API to import the various utilities in your own project,
  e.g. query-like path extraction.


```{literalinclude} ../../tests/scenario1/main.zoml
---
language: yaml
linenos: true
caption: Toy example written with ZOTI-YAML. Check the [Tutorial](tutorial) for an explanation.
---
```

This language extensions has been developed as a convenience frontend
for the [ZOTI](https://ericsson.github.io/zoti/) project and its
tools, but can also be used as an independent tool.


## Documentation pages

```{toctree}
:maxdepth: 2

tutorial

syntax-reference

api-reference
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
