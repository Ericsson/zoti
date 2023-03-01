# Template Libraries

Template libraries are a key part of ZOTI-Gen and enable the
collaborative development, organization and usage of templates from
different sources and for different target platforms.

## Template Modules

Instead of providing an own library management system, ZOTI-Gen choses
to "piggyback" on the already-established [module and package
system](https://docs.python.org/3/tutorial/modules.html) of
Python. Hence ZOTI-Gen template libraries are developed as regular
Python packages, taking advantage of the following features:

* the ability to organize components containing templates into modules
  and sub-modules according to a certain design classification;
  
* both the [API
  documentation](https://wiki.python.org/moin/DocumentationTools) tool
  ecosystem for Python projects and the CI/CD features that come with
  developing a software project.
  
* the ability to define different packages of components under various
  MIT-compatible licenses (both open-source and proprietary) and use
  them together in the same code generation flow;

* the ability to enhance template components (whose principal purpose
  is to contain specification data) with custom program logic used for
  various purposes, e.g., to verify the sanity of the importer.

In short, ZOTI-Gen template libraries are [Python
packages](https://docs.python.org/3/tutorial/modules.html) exporting
user-defined *template components*. Each template component is a child
class inheriting the {class}`zoti_gen.core.Block` base class and
partially defining its members. 

## Referencing Template Components

A template component can be instantiated from the ZOTI-Gen input
specification through the `type` entry of blocks. For example,
consider the `Baz` component defined in module `Foo.Bar`:

```python
# module Foo.Bar

from dataclasses import dataclass
from zoti_gen import Block, Requirement

@dataclass
class Baz(Block):
	code: str = "Hello {{ param.world }}!"
    requirement: Requirement = field(
        default=Requirement({"include": ["<stdio.h>"]})
    )
```

Provided that `Foo.Bar` is accessible from the ZOTI-Gen tool (e.g., by
including its root to PYTHONPATH), then the specification


```yaml
block:
- name: baz
  type: {module: "Foo.Bar", name: "Baz"}
  param: {world: World}
```

is equivalent to

```yaml
block:
- name: baz
  param: {world: World}
  code: |
    Hello {{ param.world }}!
  requirement: 
    include: ["<stdio.h>"]
```


## Developing Template Components

*NOTE: All utilities in this section are re-exported by `zoti_gen`.*

### Auto-Generated (Mandatory) Schema

Since each component is a different class, we need to use separate
schemas for input deserialization and validation. Luckily ZOTI-Gen
provides a class wrapper for inheriting a base schema with default
definition;

```{eval-rst}
.. autofunction:: zoti_gen.util.with_schema
```

Alternatively, if a custom validation schema is required, it should be
defined accordingly.

### Including code from external sources

The main reason to have template libraries is not to have to deal with
target-specific code during the synthesis process, but rather to
"pick-and-place" from a set of pre-written (and ideally pre-validated)
components. As such, most of the time the main reason to define a
template component would be for its `code` member. Since Python
strings are not ideal for developing in target-specific syntax,
ZOTI-Gen provides the following utility:

```{eval-rst}
.. autofunction:: zoti_gen.util.read_template
```

### Validator hook

While schema validation is important, it does not suffice when the the
current component has some specific dependencies based on its context
and relation with other blocks. Hence the developer can define a
member function ``check`` which is called by the renderer after
resolving the entire code blocks structure, for example: 

```python
def check(self):
	assert "format" in self.param
	assert "arg" in self.label
```

### Documentation

Do not forget to use
  [docstrings](https://www.programiz.com/python-programming/docstrings)
  and an [API
  documentation](https://wiki.python.org/moin/DocumentationTools) tool
  of your choice to document your template libraries. A library is not
  of much use if no one can use it. Make sure you mark clearly and
  visibly what is the purpose, content and requirements for each
  component in order to facilitate its finding and proper usage in
  synthesis flows.
