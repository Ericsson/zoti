import inspect
import os
import sys
from enum import Flag
from typing import Any, Optional

from sphinx.ext import autodoc
from docutils.statemachine import StringList

sys.path.insert(0, os.path.abspath("../../src/"))
from zoti_yaml import __version__

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
]

templates_path = []
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
