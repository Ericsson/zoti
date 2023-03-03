from dataclasses import dataclass, field
from zoti_gen import with_schema, Block


@with_schema(Block.Schema)
@dataclass
class Infinite(Block):
    """ The base C implementation for an infinite loop. """

    code: str = field(
        default="\
while (1) { \n\
  {% for inst in param.schedule %} \n\
  {{ placeholder[inst] }} \n\
  {% endfor %} \n\
}"
    )

    def check(self):
        assert "schedule" in self.param
        assert isinstance(self.param["schedule"], list)
