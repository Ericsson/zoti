# The Target-Agnostic Core

## Hashables

Theses classes are used for identifying types which have been bound
and loaded to theirrepective module.

```{eval-rst}
.. automodule:: zoti_ftn.core
	:members: Uid, Entry
	:show-inheritance:
	:undoc-members:
	:exclude-members: Field, Schema
```

## Base Attributes

These AST objects are used to encode base attributes in type
definitions, but are not *types* per-se.


```{eval-rst}
.. automodule:: zoti_ftn.core
	:members: Endian, IntBase, Range, Constant
	:show-inheritance:
	:undoc-members:
	:exclude-members: Field, Schema
```

## Core Data Types

These classes encode the target-agnostic type representations.

```{eval-rst}
.. automodule:: zoti_ftn.core
	:members: TypeABC, Void,  Boolean, Integer, Array, Structure, TypeRef
	:show-inheritance:
	:undoc-members:
	:exclude-members: Field, Schema
```

## The Type Database Handler


```{eval-rst}
.. autoclass:: zoti_ftn.core.FtnDb
	:members:
	:undoc-members:
```
