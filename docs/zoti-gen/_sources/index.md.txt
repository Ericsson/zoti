# ZOTI-Gen

ZOTI-Gen(erator) is a ligtweight template-based code generator. It
builds upon

1. Python's
[packaging](https://realpython.com/python-modules-packages/) and
distribution ecosystem for defining maintainable libraries of
templates; and
1. [Jinja2](https://jinja.palletsprojects.com)'s templating capabilities
for gluing together these templates. 

to define a minimalistic component-based framework for describing code
in a language- and target-agnostic manner. It is meant to serve as a
backend in a generic code synthesis flow, and has been developed in
the context of the [ZOTI](https://ericsson.github.io/zoti) project.

## Documentation pages

```{toctree}
:maxdepth: 2

input-format

template-libs

rendering

tutorial

api-reference
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
