# Syntax Reference


ZOTI-YAML sources are files following the [YAML 1.1 language
specification](https://yaml.org/spec/1.1/#id857168). To aid organizing
information into separate libraries and modules, ZOTI-YAML provides a
set of language extensions, such as references and a module system.

## Modules

Modules are the main organization units in ZOTI-YAML projects. Each
module name needs to reflect the path of its associated source
file. Assuming the search path for ZOTI modules is set to `ZOTI_PATH`
(see [Configuration](#configuration)), then the file
`ZOTI_PATH/path/to/MyModule.yaml` would correspond to the qualified
module name `path.to.MyModule`.

Each module consists in a YAML source file formatted as:

```{code-block} yaml
preamble
---
document
```

where `preamble` contains directives, such as import declarations,
descriptions or other document-wide definitions, whereas
`document` contains the actual source code.


## Preamble


A module's peramble is for the most part a free-form dictionary
containing metadata preserved and used by downstream tools. Out of
these entries, ZOTI-YAML uses two:


`module` *(string)*
: Mandatory field containing the qualified module
  name. It *needs* to reflect its path relative to the [loading
  path](#modules), otherwise an error is raised upon its loading.


`import` *(list)*
: List of imports. Each entry is a dictionay:
  :`module`:  *(string)* qualified name of module being imported.
  :`as`: *(string)* short alias used in the document.

## Document

### Commands

ZOTI-YAML documents are regular YAML files that might contain some
additional keywords followed by certain arguments, as documented
below.

#### `!default` [*defaults*, *originals*]

```{eval-rst}
.. autosimple:: zoti_yaml.core.Default
```

#### `!policy:<merge_policy>` *any*

```{eval-rst}
.. autosimple:: zoti_yaml.core.MergePolicy
```

#### `!ref` {*module*, *path*, *name*}

```{eval-rst}
.. autosimple:: zoti_yaml.core.Ref
```

#### `!attach` {*ref*, ...}

```{eval-rst}
.. autosimple:: zoti_yaml.core.Attach
```

#### `!include` {*file*, *name*|(*begin*, *end*)}

```{eval-rst}
.. autosimple:: zoti_yaml.loader.ZotiLoader.include
```


## Position Information

In addition to the explicit behavior controlled with
[commands](#commands), ZOTI-YAML implicitly stores positional metadata
for certain keys under an entry at `_info/_pos`. Exactly which nodes
are marked for metadata is controlled via:

- the CLI flag `--keys`, see [below](#configuration);
- the API, with the constructor for {class}`zoti_yaml.project.Project`.

For each key in the provided list, ZOTI-YAML will mark all first
children of its entry, provided that the children are objects
themselves. For example, if `keys` is set to `["root", "node"]`, here
is how a processed yaml file could look like:

```{code-block} yaml
root:
- name: a                 # marked, child of "root"
  _info: {_pos: ...}
  foo:
    node:
    - name: b             # marked, child of "node"
      _info: {_pos: ...}
    - bar: baz            # marked, child of "node"
      _info: {_pos: ...}
- name: b                 # marked, child of "root"
  _info: {_pos: ...}
  foo: bar
- baz                     # not marked, not an object
```

The positional metadata at `_info/_pos` is presented as a list of
entries containing positional information. The last entry in a list
corresponds to the current position in the file. Every time a (marked)
node is parsed by ZOTI-YAML its current position is appended at the
end of the list. This mean that certain nodes can be "handed over"
between tools, and ZOTI-YAML will keep the history of their positions
(e.g. in intemediate files). In the following example the shown node
has been pre-processed by ZOTI-YAML in preparation for two other tools
(ZOTI-Graph and ZOTI-Gen), and its information has resided in two
different files.

```{code-block} yaml
_info:
  _pos:
    - [36, 14, 1066, 1220, app/ProdCons/Src.zog, zoti-graph-0.1.0]
    - [20, 8, 740, 906, gen/graph/ProdCons.yaml, zoti-gen-0.1.0]
```

Check the [API Reference](api-reference) for what each field means.

## Configuration

The CLI tool can be run like any Python module depending on how it is
distributed. Configuration arguments are documented by passing
`--help`. Each configuration parameter can be specified also in a
[TOML](https://toml.io/en/) file called `zoticonf.toml` found in the
current folder, under the following sections:

```{code-block} toml
[zoti]

# global configuration variables, read by all tools

[zoti.yaml]

# configuration variables for ZOTI-YAML. override global ones

[zoti.yaml.<class>]

# specialized configuration loaded with:
#
#      $(ZOTI_YAML) --spec <class>
#
# where <class> is replaced with an arbitrary name. Overrides 
# parameters in [zoti.yaml]
```
