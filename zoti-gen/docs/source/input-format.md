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

A reference is an entry pointing to an object by its qualified name
and/or path. Since ZOTI-Gen documents are flat (i.e., they consist in
a flat list of block descriptions), and the only objects referenced in
ZOTI-Gen are blocks, the only access mechanism implemented is
referencing by (block) name. Hence every reference entry will have the
following mandatory fields:

`module` *(string)*
: the full (dot-separated) name of module containing the referenced
  block, even if that means the current module.
  
`name` *(string)*
: the name of the referenced block.

For less verbose reference syntax one could check the `!ref` keyword
in the [ZOTI-YAML][zoti-yaml] language extension and pre-processor.

## Template Function


```{eval-rst}
.. autosimple:: zoti_gen.core.TemplateFunField
```

## Code Template

The bulk of a block is its template which will be expanded as target
code. The template uses a
[Jinja2](https://jinja.palletsprojects.com/en/3.1.x/templates/) syntax
where the rendering context is formed from some of the parent block's
resolved specification entries, more precisely:

* all [`label`](#label) entries with updated information (i.e.,
  `name`, `usage` and `glue`) reflecting the block's bindings.
  
* all `param` entries updated according to the block's bindings.


```{eval-rst}
.. autosimple:: zoti_gen.render.JinjaExtensions
	:members:
	:undoc-members:
```

[zoti-yaml]: https://ericsson.github.io/zoti/zoti-yaml
