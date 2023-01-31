ZOTI-Gen
========

ZOTI-Gen is a ligtweight template-based code generator. It builds upon
Python's packaging and distribution ecosystem (for defining
maintainable libraries of templates) and
[Jinja2](https://jinja.palletsprojects.com)'s templating capabilities
(for gluing together these templates) to define a minimalistic
component-based framework for describing code in a language- and
target-agnostic manner. It is meant to serve as a backend in a generic
code synthesis flow, and has been developed in the context of the
[ZOTI](https://ericsson.github.io/zoti) project.

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
cd path/to/zoti-gen
pipenv install # --dev
pipenv run python3 -m build
```

To run the CLI tool either call it from inside the Pipenv shell:

```shell
pipenv shell
python -m zoti_gen --help
```

or from outside it, in the folder where the `Pipfile` resides:

```shell
pipenv run python3 -m zoti_gen --help
```

The API library can be loaded like any other Python package, e.g., by
adding the following path to the `PYTHONPATH` variable:

```
PYTHONPATH=${PYTHONPATH}:</path/to/>zoti-gen/src
```

ideally from within the Pipenv shell which takes care of the library
dependencies.

### Testing the library

To run the test suite, call from within a `--dev` Pipenv environment:

```shell
pytest # --cov
```

Documentation
-------------

The ZOTI-Graph input syntax, CLI tool usage and API documentation can
be found on the project [web
page](https://ericsson.github.io/zoti/zoti-gen). CLI arguments are
also documented using the `--help` flag.
