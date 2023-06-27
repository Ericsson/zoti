# Rendering

*DISCLAIMER: This page is meant to be a collection of user notes on
the internal functioning of ZOTI-Gen, and not a comprehensive
documentation resource. As such, it may fall out-of-sync with future
iterations of the tool. For advanced usage always check the source
code.*


## Code Blocks Structure

Once the input specification is loaded into a
{class}`zoti_gen.handler.ProjHandler`, the internal structure of a
project (representing a target artifact file) can be constructed
recursively using the {meth}`zoti_gen.handler.ProjHandler.resolve`
method. During this process all code templates are fully expanded and
all names are resolved, updating the internal representation of each
block accordingly. At the end of the procedure:

* all (recursively) instantiated blocks will contain resolved
  information (e.g. updated label names) and complete target code.
  
* the history of fully-expanded blocks will be reflected in
  {attr}`zoti_gen.handler.ProjHandler.decls` which contains the names
  of the top-level blocks and the order in which they need to be
  declared.
  
* the global requirements will be represented in (a dictionary of)
  graphs in {attr}`zoti_gen.handler.ProjHandler.requs`

The procedure starts with the main block pointed by
{attr}`zoti_gen.handler.ProjHandler.main` and recurs base on all the
`instance` entries found. For each block it roughly follows the
same algorithm:

1. resolve the component name to avoid clashes in the same namespace.

1. foreach original `label` resolve label name to avoid clashes

1. update `param` based on bindings

1. foreach original `label` render its usage in the current
   context

1. foreach `instance`:
   - retrieve referenced block
   - resolve bindings
   - recursive call block resolver and/or code renderer based on
     instance `directive`

1. if current block has requirements update the global ones

1. render `code` in the current context. If annotations specified
   surround rendered code with annotations.

## Controlling Block Instantiation

There are several way to control how a block is going to be
instantiated or rendered. This section goes through some of the more
common use cases.

### Inline code expansion

The code of a block can be expanded in another block's placeholder in
the following case:

* the `instance/directive` entry contains the flag `"expand"`.

* if the `instance/usage` entry is provided then the (recursively
  expanded) code of the referenced block passes through an additional
  rendering in the current context to reflect its usage.
  
* if the referenced block contains a `block/prototype` entry it will
  be ignored.
  
### Function call

If the instantiated block needs to be expanded as an independent
(declared) function instead of an inline snippet, which is called from
the parent's placeholder here is how to do this:

* do not pass anything to `instance/directive`.

* define a function call template in `instance/usage`.

* define a function type signature in the referenced block's
  `block/prototype`.

NOTE 1: if multiple parent blocks reference the same block, it will
only be declared (and constructed) once, and all subsequent calls will
be handled by `instance/usage`. If this is not the desired behavior
and you need to create separate new declarations of the same block
(with new names) for each new instance, you need to 

* provide the flag `"new"` to each `instance/directive` concerned.

NOTE 2: by default, when constructing a new declaration for the
instantiated component the parent's namespace is reset, and the label
bindings are not passed further to the referenced block. If this is
not the desired behavior, i.e., you need to pass forward name
bindings, you need to 

* provide the flag `"pass"` to `instance/directive`.

### New declaration without function call

If we just need to trigger the resolve of certain blocks but without
being referenced in the rendered code, you can follow the instructions
for [](#function-call) with the following addition:

* do not provide `instance/placeholder` or leave it empty or set it to
  `null`.
