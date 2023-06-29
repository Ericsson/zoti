# The Script Handler

The {mod}`zoti_graph.script` module is meant to help getting started
with building an own transformation-based code synthesis flow
following the ZOTI methodologies or principles. It contains some
function drivers that may (or may not) be used when describing
transformation scripts.

## Script Handler 

```{eval-rst}
.. autoclass:: zoti_graph.script.Script
	:members:

.. autoclass:: zoti_graph.script.TransSpec
	:members:
```

## Useful Exceptions

```{eval-rst}
.. autoclass:: zoti_graph.exceptions.ScriptError
	:members:

.. autoclass:: zoti_graph.exceptions.ContextError
	:members:
	
.. autoclass:: zoti_graph.exceptions.EntryError
	:members:
```
