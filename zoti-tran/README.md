ZOTI-Tran
=========

ZOTI-Tran(sformations) is a simple skeleton project to help getting
started with building an own transformation-based code synthesis
flow. It contains some function drivers that may (or may not) be used
when describing transformation scripts, as well as a small set of
generic (platform-agnostig)
[ZOTI-Graph](https://ericsson.github.io/zoti/zoti-graph/)
transformations.

https://ericsson.github.io/zoti/zoti-tran

Installation & Usage
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

### Library

In the cloned root folder run the following installation
commands. Uncomment the `--dev` flag if you plan on developing the
code or running the test suite.

```shell
cd path/to/zoti-tran
pipenv install # --dev
pipenv run python3 -m build
```

The API library can be loaded like any other Python package, e.g., by
adding the following path to the `PYTHONPATH` variable:

```
PYTHONPATH=${PYTHONPATH}:</path/to/>zoti-tran/src
```
from an environment where its dependencies (see [Pipfile](Pipfile)) are met,
(e.g. from within this `pipenv` shell). Alternatively, one can build
the package in the scope of a separate virtual environment:

```
pipenv install -e </path/to/>zoti-tran
```

Documentation
-------------

API documentation can be found on the project [web
page](https://ericsson.github.io/zoti/zoti-tran).
