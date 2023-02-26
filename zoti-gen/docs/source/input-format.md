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
[`zoti_yaml.Module`](../zoti-yaml) container, hence input files
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

<!-- Every entry under the `block` key would fill in the corresponding -->
<!-- member in the {class}`Block` class below. Apart from that, blocks -->
<!-- might contain an additional `type` entry which points to an externally -->
<!-- defined library template which would fill in the corresponding entries -->
<!-- as documented in [](template-libs). -->

```{eval-rst}
.. autosimple:: zoti_gen.core.Block.Schema
	:members:
	:exclude-members: Schema
```

#### `requirement`

```{eval-rst}
.. autosimple:: zoti_gen.core.RequirementSchema
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

## Template Function

## Code Template

```{eval-rst}
.. autoclass:: zoti_gen.render.JinjaExtensions
	:members:
	:undoc-members:
```
