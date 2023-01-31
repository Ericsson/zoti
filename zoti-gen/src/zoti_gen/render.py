import logging
import operator
import sys
from functools import reduce
from typing import Any, Dict

from jinja2 import Environment, Template, pass_context

from zoti_gen.core import LabelSchema
from zoti_gen.exceptions import TemplateError


class JinjaExtensions:
    """Namespace class gathering all functions that are extending the
    Jinja syntax during template evaluation."""

    @staticmethod
    def find(json: Dict, path: str):
        """Returns the element with (the dot-separated) **path** in a
        **json** dictionary."""
        return reduce(operator.getitem, path.split("."), json)

    @staticmethod
    def setdefaults(json: Any, defaults: Dict) -> Dict:
        """For every direct child of the given **json** element it (possibly
        recursively) sets the **defaults** values if undefined. E.g.:

            >>> json = {'a': None, 'b':{'foo':'bar'}}
            >>> defaults {'foo':'biff', 'baz':'buzz'}
            >>> setdefaults(json, defaults)
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
    def eval(context, value):
        return Template(value).render(context)

    @staticmethod
    def error(msg: str, *args):
        """TODO"""
        raise Exception(msg.format(*args))

    @staticmethod
    @pass_context
    def getter(context, elem, *args):
        lab, path = (elem.split(".", 1) + [''])[:2]
        try:
            glue = context["label"][lab]["glue"]
            prefix = glue.get("prefix", "") if glue else ""
            name = prefix + context["label"][lab]["name"]
            expargs = ",".join([name] + list(args))
            expr = JinjaExtensions.find(glue, path)["_get"] if path else glue["_get"]
            return f"{expr}({expargs})"
        except Exception as e:
            from pprint import pformat
            msg = f"Cannot get element '{path}' from label '{lab}'"
            msg += f" in the context:\n {pformat(context['label'])}"
            print(msg)
            raise Exception

    @staticmethod
    @pass_context
    def setter(context, elem, *args):
        lab, path = (elem.split(".", 1) + [''])[:2]
        try:
            glue = context["label"][lab]["glue"]
            prefix = glue.get("prefix", "") if glue else ""
            name = prefix + context["label"][lab]["name"]
            expargs = ",".join([name] + list(args))
            expr = JinjaExtensions.find(glue, path)["_set"] if path else glue["_set"]
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
        raise TemplateError(template, err_line=lineno, err_string=repr(msg), info=info)

#######################

# >>> x
# '{{ (param.d | find(param)).b | eval }}'
# >>> ctx
# {'a': {'b': 'HALLÅ {{param.c}}'}, 'c': 'WÖRLD!', 'd': 'a'}
# >>> r.code(x, params=ctx)
# 'HALLÅ WÖRLD!'
