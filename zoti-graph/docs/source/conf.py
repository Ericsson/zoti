import inspect
import os
import sys
from enum import Flag
from typing import Any, Optional

from sphinx.ext import autodoc
from docutils.statemachine import StringList

sys.path.insert(0, os.path.abspath("../../src/"))
from zoti_graph import __version__


project = "zoti-graph"
copyright = "2022-2023 Ericsson"
author = "George Ungureanu"

# The full version, including alpha/beta/rc tags
release = __version__


extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "myst_parser",
]

myst_enable_extensions = [
    "colon_fence",
    "fieldlist",
    "html_admonition",
    "html_image",
]

html_theme_options = {
    'github_button': True,
    'github_user': 'Ericsson',
    'github_repo': 'zoti',
    'extra_nav_links': {
        "ZOTI": "https://ericsson.github.io/zoti/",
        "GitHub": "https://github.com/Ericsson/zoti/tree/main/zoti-graph",
    }
}

templates_path = []
exclude_patterns = []
autodoc_member_order = "bysource"
add_module_names = False
myst_heading_anchors = 3


class MyClassDocumenter(autodoc.ClassDocumenter):
    objtype = "simple"
    priority = autodoc.ClassDocumenter.priority - 10
    option_spec = dict(autodoc.ClassDocumenter.option_spec)

    # do not indent the content
    content_indent = ""

    def format_args(self):
        return None

    # do not add a header to the docstring
    def add_directive_header(self, sig):
        pass


class FlagDocumenter(autodoc.ClassDocumenter):

    objtype = "intflag"
    directivetype = "class"
    priority = 10 + autodoc.ClassDocumenter.priority
    option_spec = dict(autodoc.ClassDocumenter.option_spec)
    # option_spec['show-inheritance'] = lambda x : False
    # option_spec['hex'] = bool_option

    @classmethod
    def can_document_member(
        cls, member: Any, membername: str, isattr: bool, parent: Any
    ) -> bool:
        return inspect.isclass(member) and issubclass(member, Flag)

    def document_members(self, all_members):
        pass

    def add_content(
        self, more_content: Optional[StringList], no_docstring: bool = False
    ) -> None:

        source_name = self.get_sourcename()
        flag_object: Type[Flag] = self.object
        self.options.show_inheritance = False

        # self.add_line('', source_name)

        content = []
        for flag_value in flag_object:
            the_value_name = flag_value.name
            the_value_value = flag_value.value
            content.append(f"**{the_value_name}**")

        self.add_line("Values = {{{}}}".format(
            ", ".join(content)), source_name)
        self.add_line("", source_name)
        super().add_content(more_content)

    def format_signature(self, **kwargs: Any) -> str:
        return ""

def setup(app):
    app.add_autodocumenter(FlagDocumenter)
    app.add_autodocumenter(MyClassDocumenter)
