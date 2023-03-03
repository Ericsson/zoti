# API Reference

Unlike most other ZOTI tools the API of ZOTI-Gen is not particularly
interesting, since it is meant to be used mainly as a CLI tool. More
important, though, is its exported core representation used when
creating [Template Libraries](template-libs), documented in its
respective page.

## The Project Handler

```{eval-rst}
.. automodule:: zoti_gen.handler
	:members:
	:undoc-members:
```

## The Code Renderer

```{eval-rst}
.. autofunction:: zoti_gen.render.code
```

## The Core Representation

All core types are re-exported by `zoti_gen` and are meant to be used
when defining template components.

```{eval-rst}
.. autoclass:: zoti_gen.core.Block
	:members:	
	:exclude-members: Schema

.. autoclass:: zoti_gen.core.Requirement
	:members:	

.. autoclass:: zoti_gen.core.Label
	:members:	

.. autoclass:: zoti_gen.core.Instance
	:members:	

.. autoclass:: zoti_gen.core.Bind
	:members:	

.. autoclass:: zoti_gen.core.Ref
	:members:	

.. autoclass:: zoti_gen.core.TemplateFun
	:members:
	
```


## Exceptions

```{eval-rst}
.. automodule:: zoti_gen.exceptions
	:members:
```
