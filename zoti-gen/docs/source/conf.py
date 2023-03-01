import inspect
import os
import sys
from enum import Flag
from typing import Any, Optional

from sphinx.ext import autodoc
from docutils.statemachine import StringList

sys.path.insert(0, os.path.abspath("../../src/"))

project = "zoti-gen"
copyright = "2022-2023 Ericsson"
author = "George Ungureanu"

# The full version, including alpha/beta/rc tags
release = "0.1.0"

extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "myst_parser",
]

myst_enable_extensions = [
    "colon_fence",
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
        "GitHub": "https://github.com/Ericsson/zoti/tree/main/zoti-tran",
    }
}

templates_path = []
exclude_patterns = []
autodoc_member_order = "bysource"
add_module_names = True
myst_heading_anchors = 4
# autodoc_typehints = "description"


autodoc_typehints_format = 'fully-qualified'
autodoc_unqualified_typehints = True


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
