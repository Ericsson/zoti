from dataclasses import dataclass, field

from zoti_gen import with_schema, Block, Template

# from pathlib import Path


__sphinx_ignore__ = True


@with_schema(Block.Schema)
@dataclass
class Infinite(Block):
    """ The base C implementation. """

    code: Template = field(
        default=Template("\
while (1) { \n\
  {% for inst in param.schedule %} \n\
  {{ placeholder[inst] }} \n\
  {% endfor %} \n\
}"))

    def check(self):
        assert "schedule" in self.param
        assert isinstance(self.param["schedule"], list)


@with_schema(Block.Schema)
@dataclass
class Composite(Block):
    """
    Triggering point for socker reception.
    """

    code: str = field(
        default=Template("""
{% for inst in param.schedule -%}
{% if not placeholder[inst] %} {{ error("No instance for placeholder '{}'",inst) }} {% endif %}
{{ placeholder[inst] }}
{%- endfor %}"""))

    def check(self):
        assert "schedule" in self.param
        assert isinstance(self.param["schedule"], list)
