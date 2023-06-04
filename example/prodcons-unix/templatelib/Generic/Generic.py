from dataclasses import dataclass, field

from zoti_gen import with_schema, Block, Template


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
}", parent="code"))

    def check(self):
        assert "schedule" in self.param
        assert isinstance(self.param["schedule"], list)


@with_schema(Block.Schema)
@dataclass
class Composite(Block):
    """
    Triggering point for socket reception.
    """

    code: str = field(
        default=Template("""
{% for inst in param.schedule -%}
{% if not placeholder[inst] %} {{ error("No instance for placeholder '{}'",inst) }} {% endif %}
{{ placeholder[inst] }}
{%- endfor %}""", parent="code"))

    def check(self):
        assert "schedule" in self.param
        assert isinstance(self.param["schedule"], list)
