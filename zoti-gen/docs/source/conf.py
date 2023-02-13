import inspect
import os
import sys
from enum import Flag
from typing import Any, Optional

from sphinx.ext import autodoc
from docutils.statemachine import StringList

sys.path.insert(0, os.path.abspath("../../src/"))

project = "zoti-tran"
copyright = "2022-2023 Ericsson"
author = "George Ungureanu"

# The full version, including alpha/beta/rc tags
release = "0.1.0"

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
        "GitHub": "https://github.com/Ericsson/zoti/tree/main/zoti-tran",
    }
}

templates_path = []
exclude_patterns = []
autodoc_member_order = "bysource"
add_module_names = True
myst_heading_anchors = 3
# autodoc_typehints = "description"


autodoc_typehints_format = 'fully-qualified'
autodoc_unqualified_typehints = True
