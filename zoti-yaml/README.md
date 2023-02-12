ZOTI-YAML
=========

A lightweight YAML language extension to support describing document
trees distributed across several modules. It consists of:

 * special keywords (e.g., `!ref`, `!attach`, `!include`, `!default`)
   that help constructing document trees with information spread
   across several files;
 * a module system, i.e. a document preamble structure and a custom
   loader;
 * a CLI tool to convert ZOTI-YAML modules to regular YAML files;
 * an API to import the loading and building utilities in your own
   project if needed.

This language extensions has been developed as a convenience frontend
for the [ZOTI](https://ericsson.github.io/zoti/) project and its
tools, but can be used independently.

https://ericsson.github.io/zoti/zoti-yaml

Installation
------------

This project is being developed as a
[pip](https://packaging.python.org/en/latest/key_projects/#pip)
package but for all intents and purposes it should be built inside a
[Pipenv](https://pipenv.pypa.io/en/latest/) sandbox until a release
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
cd path/to/zoti-yaml
pipenv install # --dev
pipenv run python3 -m build
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
python -m zoti_yaml --help
```

or from outside it, in the folder where the `Pipfile` resides:

```shell
pipenv run python3 -m zoti_yaml --help
```

CLI arguments documented with the `--help` command can be also passed
via a `zoticonf.toml` file situated in the same path where the tool is
being invoked. Arguments need to be defined under a section called
`[zoti.yaml]` and need to follow [TOML](https://toml.io/en/v1.0.0)
syntax, e.g.:

```toml
[zoti]

# global configuration variables, read by all tools. Unused.

[zoti.yaml]

# configuration variables for ZOTI-YAML. override global ones

[zoti.yaml.<class>]

# specialized configuration loaded with:
#
#      $(ZOTI_YAML) --spec <class>
#
# where <class> is replaced with an arbitrary name. Overrides 
# variables in [zoti.yaml]
```

### API library

The API library can be loaded like any other Python package, e.g., by
adding the following path to the `PYTHONPATH` variable:

```
PYTHONPATH=${PYTHONPATH}:</path/to/>zoti-yaml/src
```

ideally from within the Pipenv shell which takes care of the
dependency on PyYAML. Alternatively, one can build
the package in the scope of a separate virtual environment:

```
pipenv install -e </path/to/>zoti-yaml
```

or even in the global scope using `pip` (not recommended yet).

Documentation
-------------

The ZOTI-YAML syntax, CLI tool usage and API documentation can be
found on the project [web
page](https://ericsson.github.io/zoti/zoti-yaml). CLI arguments are
also documented using the `--help` flag.

An inline documented test example can be found in
[`zoti-yaml/tests/scenario1`](tests/scenario1). This example is
thoroughly explained on the [web
page](https://ericsson.github.io/zoti/zoti-yaml/tutorial).


