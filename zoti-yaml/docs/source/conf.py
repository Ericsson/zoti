import inspect
import os
import sys
from enum import Flag
from typing import Any, Optional

from sphinx.ext import autodoc
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
# from sphinx_toolbox.sidebar_links import SidebarLinksDirective

sys.path.insert(0, os.path.abspath("../../src/"))
from zoml import __version__

project = "zoti-yaml"
copyright = "2023, Ericsson S&T"
author = "George Ungureanu"
release = __version__

extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "myst_parser",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "html_admonition",
    "html_image",
    "deflist",
]

html_theme_options = {
    'github_button': True,
    'github_user': 'Ericsson',
    'github_repo': 'zoti',
    'extra_nav_links': {
        "ZOTI": "https://ericsson.github.io/zoti/",
        "GitHub": "https://github.com/Ericsson/zoti/tree/main/zoti-yaml",
    }
}

exclude_patterns = []
# html_static_path = ["_static"]
autodoc_member_order = "bysource"
add_module_names = False
autodoc_inherit_docstrings = False
myst_heading_anchors = 3


class SimpleClassDocumenter(autodoc.ClassDocumenter):
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

def setup(app):
    app.add_autodocumenter(SimpleClassDocumenter)
