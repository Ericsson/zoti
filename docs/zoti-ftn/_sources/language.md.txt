# The ZOTI-FTN Language


The ZOTI-FTN language consists in a small syntax used for describing
data types. ZOTI-FTN files represent modules and can have the
following structure:


```{literalinclude} ../../src/zoti_ftn/lang.py
---
lines: 45-49
---
```

A module consists in multiple bindings from names to type
specifications, as specified in the following parser rules:

```{literalinclude} ../../src/zoti_ftn/lang.py
---
lines: 19-39
---
```

The attributes (`attrs`) differ for different types, and the allowed
enties are documented in the AST schemas (e.g., for the
[target-agnostic AST](agnostic) or the [C-specific
AST](backend-c)). The allowed keywords are:


```{literalinclude} ../../src/zoti_ftn/tokens.py
---
---
```

To parse an input file into its AST one can use the CLI tool
associated with this package, e.g.

```
python3 -m zoti_ftn -h
```
