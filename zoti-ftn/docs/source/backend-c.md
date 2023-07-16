# The C-Specific Core

The API of the C-specific core is meant to aid in generating glue code
in the C language for the represented types. Method naming roughly
follows the convention:

* `<name>`: utility function. One should check the type signature and
  documentation to find out its purpose.
* `gen_<name>`: method that generates a list of "naked" C statements
  in the sense that the caller needs to properly format them and add
  separators.
* `gen_<name>_expr`: method that generates a (sub-)expression of a
  statement. Used by the caller in building statements.


```{eval-rst}
.. autoclass:: zoti_ftn.backend.c.FtnDb
	:members:
	:undoc-members:
	:inherited-members:
	:show-inheritance:
```

```{eval-rst}
.. automodule:: zoti_ftn.backend.c
	:members:
	:inherited-members:
	:show-inheritance:
	:undoc-members:
	:exclude-members: Schema, Field, TypeABC, FtnDb
```

