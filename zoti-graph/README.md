ZOTI-Graph
==========

This is a Python implementation of the core representation of
[ZOTI](https://github.com/Ericsson/zoti) system models. These models
are hierarchical graph-like structures representing system elements
such as kernel computations, actors, ports, platform nodes,
dependencies, etc. For a full documentation on ZOTI-Graph, as well as
links to the ZOTI project, please refer to the [project web
page](https://ericsson.github.io/zoti/zoti-graph).

This project currently consists in:

 * a core representation of the ZOTI model graphs based mainly on
   [networkx](https://networkx.org/) as a host DSL;

 * an extensive API for manipulating and analyzing ZOTI model graphs,
   possibly extendable with [networkx](https://networkx.org/) graph
   tools;

 * an input format and set of schema parsers for
   serializing/deserializing models to/from JSON/YAML;
  
 * a Graphviz plotter;

 * a CLI tool for basic operations on system graphs. 
  
This core representation format is designed to be used within the
[ZOTI](https://ericsson.github.io/zoti) tool ecosystem, but it can be
used as a standalone tool as well. The input format is designed to be
machine-friendly (not user-friendly) and is verbose on purpose. For
advanced input syntax and utilities we recommend specifying the system
graph using the [ZOTI-YAML](https://ericsson.github.io/zoti/zoti-yaml)
language extension.

Installation
------------

This project is being developed as a
[pip](https://packaging.python.org/en/latest/key_projects/#pip)
package but for all intents and purposes it should be built inside a
[Pipenv](https://pipenv.pypa.io/en/latest/) sandbox until a stable release
version comes out.

### Dependencies:

Make sure you have some newer versions of Python
[pip](https://pip.pypa.io/en/stable/) and
[Pipenv](https://pipenv.pypa.io/en/latest/). An example installation
on a Debian-based Linux distro using [pipx](https://pypa.github.io/pipx/):

```shell
sudo apt install python3 python3-venv
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install pipenv
```

### Tool and library

In the cloned root folder run the following installation
commands. Uncomment the `--dev` flag if you plan on developing the
code or running the test suite.

```shell
cd path/to/zoti-graph
pipenv install # --dev
pipenv run python3 -m build
```

### Testing the library

To run the test suite, call from within a `--dev` Pipenv environment:

```shell
pipenv run pytest # --cov
```

### Generating the API documentation locally

To generate the API documentation you need the `sphinx-build` tool,
already included in the `--dev` environment.

```shell
cd path/to/zoti-yaml/docs
sphinx-build -M [target] source build
```

where `[target]` is one of the targets documented when typing 

```shell
sphinx-build -M help source build
```

Usage
-----

### CLI tool

To run the CLI tool either call it from inside the Pipenv shell:

```shell
pipenv shell
python -m zoti_graph --help
```

or from outside it, in the folder where the `Pipfile` resides:

```shell
pipenv run python3 -m zoti_graph --help
```

CLI arguments documented with the `--help` command can be also passed
via a `zoticonf.toml` file situated in the same path where the tool is
being invoked. Arguments need to be defined under a section called
`[zoti.graph]` and need to follow [TOML](https://toml.io/en/v1.0.0)
syntax, e.g.:

```toml
[zoti]

# global configuration variables, read by all tools. Unused.

[zoti.graph]

# configuration variables for ZOTI-Graph. Overrides global ones

output = "gen/graph/app.json"
dump_out = "gen/dbg"
dump_graph = true
dump_args.root: "/Sys/Platform1"
dump_args.depth: 3
```

### API Library

The API library can be loaded like any other Python package, e.g., by
adding the following path to the `PYTHONPATH` variable:

```
PYTHONPATH=${PYTHONPATH}:</path/to/>zoti-graph/src
```

from an environment where its dependencies (see [](Pipfile)) are met,
(e.g. from within this `pipenv` shell). Alternatively, one can build
the package in the scope of a separate virtual environment:

```
pipenv install -e </path/to/>zoti-graph
```

or even in the global scope using `pip` (not recommended yet).

Documentation
-------------

Model and API documentation can be found on the project [web
page](https://ericsson.github.io/zoti/zoti-graph). CLI arguments are
also documented using the `--help` flag.
