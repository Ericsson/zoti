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

```{code-block} yaml
---
caption: Toy example written with ZOTI-YAML. Check the [Tutorial](tutorial) for an explanation.
---	
module: main
import:
  - {module: mod1}
  - {module: sub.mod, as: mod2}

---

!default
- root:
    - mark: !with_create DEFAULT_MARKING
- root:
  - name: n1
    nodes:
      - name: n1_n1
        nodes:
          - name: n1_n1_n1
            data:
              !attach
              ref: !ref {path: "../../../nodes[n1_n2]/extra"}
      - name: n1_n2
        extra: "I am referenced by n1_n1_n1!"
        data:
          !attach
          ref: !ref {module: mod1, path: "/root/node[n_who]/data"}
  - !attach
    ref: !ref {module: mod2, path:  "/root/nodes[n1]"}
    name: n2
    content-extra: "I will be ignored!"
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
