# Input Specification

ZOTI-Gen structures are specified using: 

* a serialization format (e.g. JSON or YAML) representing the
  structure of the code blocks, their hierarchy and bindings;

* an extended [Jinja2](https://jinja.palletsprojects.com) template
  format contained as strings by the `code` entries of the
  serialization format.
  
* a simpler [templated
  string](https://docs.python.org/3/library/string.html#template-strings)
  format to define glue macros in some of the binding entries.

## Format Schema

ZOTI-Gen input files are describing code blocks using a serialization
format. Similarly to other ZOTI tools, ZOTI-Gen stores modules in a
[ZOTI-YAML][zoti-yaml] container, hence input files
contain the arguments passed to its constructor, among which a
*preamble* object and a *document* object.


### Preamble

Apart from the mandatory *module* entry containing the qualified name
of the current module, ZOTI-Gen preambles need to contain the
following entry:

`top` *(string)*
: the name of the "top" block from which all other blocks are
  recursively referenced.
  
  
### Document

A ZOTI-Gen document consists in a list of `block` entries. Each entry
would fill in an equivalent class container hence we use the class API
documnentation to document the entry schemas.

#### `block`

```{eval-rst}
.. autosimple:: zoti_gen.core.Block.Schema
	:members:
	:exclude-members: Schema
```

#### `requirement`

```{eval-rst}
.. autosimple:: zoti_gen.core.RequirementField
```

#### `label`

```{eval-rst}
.. autosimple:: zoti_gen.core.LabelSchema
```

#### `instance`

```{eval-rst}
.. autosimple:: zoti_gen.core.InstanceSchema
```

#### `bind`

```{eval-rst}
.. autosimple:: zoti_gen.core.BindSchema
```

## Reference

```{eval-rst}
.. autosimple:: zoti_gen.core.RefSchema
```


## Code Template

Code templates are strings with
[Jinja2](https://jinja.palletsprojects.com/en/3.1.x/templates/) markup
commands evaluated in a custom context built from the resolved block
specification. Depending on its role in the input specification (see
documentation above), each template is evaluated and rendered using a
custom context built from resolved information from the interal
representation, most usually having the following context fields:

:label: contains a dictionary of all resolved `label` entries (see
    [](input-format)), both own and passed via bindings, where the
    keys are the original (specified) names. Each entry contains
    possibly updated information (i.e., `name`, `usage` and `glue`)
    reflecting the block's bindings.

:param: usually contains a merged dictionary with this block's `param`
    entries and the ones passed via bindings.

:placeholder: will contain rendered code blocks for various declared
    instances (e.g., as inline code or function call) in the current
    block's scope.

```{eval-rst}
.. autosimple:: zoti_gen.jinja_extensions.JinjaExtensions
	:members:
	:undoc-members:
```

[zoti-yaml]: https://ericsson.github.io/zoti/zoti-yaml
