ZOTI-FTN
========

This implementation of ZOTI-FTN (Flexible Type Notation) is an early
prototype for a tool and language for describing and synthesizing code
for *data types* in the context of a
[ZOTI](https://ericsson.github.io/zoti) synthesis flow.

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
cd path/to/zoti-ftn
pipenv install # --dev
pipenv run python3 -m build
```

*ATTENTION*: the CLI tool can only be used for parsing the in-house
FTN language to plain JSON. The code synthesis features are not
functional. For some early code synthesis features you need to
exclusively use the API.

To run the CLI tool either call it from inside the Pipenv shell:

```shell
pipenv shell
python -m zoti_ftn --help
python -m zoti_ftn parse --help
```

or from outside it, in the folder where the `Pipfile` resides:

```shell
pipenv run python3 -m zoti_ftn --help
```

The API library can be loaded like any other Python package, e.g., by
adding the following path to the `PYTHONPATH` variable:

```
PYTHONPATH=${PYTHONPATH}:</path/to/>zoti-ftn/src
```

To run the test suite, call from within a `--dev` Pipenv environment:

```shell
pytest # --cov
```
