import inspect
import os
import sys
from typing import Any, Optional

from sphinx.ext import autodoc
from docutils.statemachine import StringList

sys.path.insert(0, os.path.abspath("../../src/"))
from zoti_ftn import __version__
from zoti_ftn.util import with_schema
from zoti_ftn.backend.c import TypeABC


project = "zoti-ftn"
copyright = "2022-2023 Ericsson"
author = "Leif Linderstam & George Ungureanu"

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
        "GitHub": "https://github.com/Ericsson/zoti/tree/main/zoti-ftn",
    }
}

templates_path = []
exclude_patterns = []
autodoc_member_order = "bysource"
add_module_names = False
myst_heading_anchors = 3


# class MyClassDocumenter(autodoc.ClassDocumenter):
#     objtype = "simple"
#     priority = autodoc.ClassDocumenter.priority - 10
#     option_spec = dict(autodoc.ClassDocumenter.option_spec)

#     # do not indent the content
#     content_indent = ""

#     def format_args(self):
#         return None

#     # do not add a header to the docstring
#     def add_directive_header(self, sig):
#         pass


class MyClassDocumenter(autodoc.ClassDocumenter):
    objtype = 'with_schema'
    directivetype = 'class'

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, TypeABC)

    
def setup(app):
    app.add_autodocumenter(MyClassDocumenter)
    pass
