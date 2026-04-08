"""Sphinx configuration for project documentation."""

#!/usr/bin/env python3

import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath("../../src"))
sys.path.insert(1, os.path.abspath("../ext"))

import fmu.settings

# -- General configuration ---------------------------------------------

extensions = [
    "myst_parser",
    # "pydantic_autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_copybutton",
]

myst_enable_extensions = [
    "substitution",
    "colon_fence",
]

# The suffix of source filenames.
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# The master toctree document.
master_doc = "index"

exclude_patterns = ["_build"]

pygments_style = "sphinx"

html_theme_options = {
    "sidebar_hide_name": False,  # Show project name in sidebar header
    "navigation_with_keys": True,  # Enable keyboard navigation
}

# General information about the project.
project = "FMU Settings"
current_year = date.today().year

release = fmu.settings.__version__
version = ".".join(release.split(".")[:2])


html_theme = "furo"
html_title = f"{project} {version}"
copyright = f"Equinor {current_year} ({project} release {release})"


# Output file base name for HTML help builder.
htmlhelp_basename = "fmu-settings"
