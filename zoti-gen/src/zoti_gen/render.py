import logging
import operator
import sys
from functools import reduce
from typing import Any, Dict

from jinja2 import Environment, Template, pass_context

from zoti_gen.core import LabelSchema
from zoti_gen.exceptions import TemplateError


class JinjaExtensions:
    """Apart from the `Jinja2 builtin functions
    <https://jinja.palletsprojects.com/en/3.1.x/templates/#list-of-builtin-filters>`_,
    ZOTI-Gen adds the following functions that can be called from
    within code templates.

    """

    @staticmethod
    def find(json: Dict, path: str) -> Any:
        """Returns the element with (the dot-separated) *path* in a *json*
        dictionary, where *path* is specified as a string. E.g.

        .. code-block:: jinja

            {# considering the context {'a': None, 'b':{'foo':{'bar': 'baz'}}} #}

            { b | find("foo.bar") }

            {# is the same as #}

            { b.foo.bar }

        both rendering ``baz``.

        """

        return reduce(operator.getitem, path.split("."), json)

    @staticmethod
    def setdefaults(json: Any, defaults: Dict) -> Dict:
        """For every direct child of the given *json* element it (possibly
        recursively) sets the *defaults* values if undefined. E.g.:

        .. code-block:: jinja

            {% set json = {'a': None, 'b':{'foo':'bar'}} %}
            {% set defaults = {'foo':'biff', 'baz':'buzz'} %}
            {% set example = setdefaults(json, defaults) %}

        results in ``example`` containing the dictionary

        .. code-block:: python

            {'a': {'foo':'biff', 'baz':'buzz'}, 'b':{'foo':'bar', 'baz':'buzz'}}

        """

        newdict = {}
        if isinstance(json, dict):
            newdict = json.copy()
        elif isinstance(json, list):
            newdict = {k: {} for k in json}
        else:
            newdict[json] = {}
        for k, v in newdict.items():
            for kd, vd in defaults.items():
                if not v:
                    newdict[k] = {kd: vd}
                elif isinstance(v, dict) and not v.get(kd):
                    newdict[k].update({kd: vd})
        return newdict

    @staticmethod
    @pass_context
    def eval(context: Dict, string: str) -> str:
        """Renders a Jinja2 string within a *context*. Useful if both *string*
        and *context* are passed to the current template context."""
        return Template(value).render(context)

    @staticmethod
    def error(msg: str, *args) -> None:
        """Raise an exception from within the template logic."""
        raise Exception(msg.format(*args))

    @staticmethod
    @pass_context
    def getter(context, elem, *args) -> str:
        """ZOTI-Gen specific formatter that retrieves the type getter macro
        created by ZOTI-FTN and stored in each label's ``glue``
        entry and creates an access expresion based on it:

        .. code-block:: jinja

            {{ getter("data.data.LEN") }}

            {# is equivalent to #}

            {{ label.data.glue.data.LEN._get }}({{ label.data.name }})

        """
        lab, path = (elem.split(".", 1) + [''])[:2]
        try:
            glue = context["label"][lab]["glue"]
            prefix = glue.get("prefix", "") if glue else ""
            name = prefix + context["label"][lab]["name"]
            expargs = ",".join([name] + list(args))
            expr = JinjaExtensions.find(
                glue, path)["_get"] if path else glue["_get"]
            return f"{expr}({expargs})"
        except Exception as e:
            from pprint import pformat
            msg = f"Cannot get element '{path}' from label '{lab}'"
            msg += f" in the context:\n {pformat(context['label'])}"
            print(msg)
            raise Exception

    @staticmethod
    @pass_context
    def setter(context, elem, *args) -> str:
        """ZOTI-Gen specific formatter that retrieves the type setter macro
        created by ZOTI-FTN and stored in each label's ``glue``
        entry and creates an access expression based on it:

        .. code-block:: jinja

            {{ setter("data.data.c", "i", "x" }}

            {# is equivalent to #}

            {{ label.data.glue.data.c._set }}({{ label.data.name }}, i, x)

        """
        lab, path = (elem.split(".", 1) + [''])[:2]
        try:
            glue = context["label"][lab]["glue"]
            prefix = glue.get("prefix", "") if glue else ""
            name = prefix + context["label"][lab]["name"]
            expargs = ",".join([name] + list(args))
            expr = JinjaExtensions.find(
                glue, path)["_set"] if path else glue["_set"]
            return f"{expr}({expargs})"
        except Exception as e:
            from pprint import pformat
            msg = f"Cannot set element '{path}' from label '{lab}'"
            msg += f" in the context:\n {pformat(context['label'])}"
            print(msg)
            raise Exception


def code(template, labels={}, params={}, blocks={}, info=None) -> str:
    """Renders the **template** in the context of **label**, **param**, and the
    (previously) rendered **blocks** that will fit inside the `placeholder`.

    Side-effect: prints **template** to the debug logger before trying to render it.
    """
    try:
        env = Environment(extensions=["jinja2.ext.do"])
        for f in [a for a in dir(JinjaExtensions) if a[0] != "_"]:
            env.filters[f] = vars(JinjaExtensions)[f].__func__
            env.globals[f] = vars(JinjaExtensions)[f].__func__
        tm = env.from_string(template)
        ctx_labels = {k: LabelSchema().dump(p) for k, p in labels.items()}
        logging.debug(f" * label = {ctx_labels}")
        logging.debug(f" * param = {params}")
        logging.debug(f" * label = {blocks}")
        logging.debug("----------------------------------------------------")
        logging.debug(template)
        logging.debug("----------------------------------------------------")
        return tm.render(label=ctx_labels, param=params, placeholder=blocks)
    except Exception:
        ty, msg, exc_tb = sys.exc_info()
        while exc_tb and "template code" not in exc_tb.tb_frame.f_code.co_name:
            exc_tb = exc_tb.tb_next
        lineno = exc_tb.tb_lineno if exc_tb else -2
        raise TemplateError(template, err_line=lineno,
                            err_string=repr(msg), info=info)
