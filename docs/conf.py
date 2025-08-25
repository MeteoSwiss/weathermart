# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = "data-provider"
copyright = "2025, MeteoSwiss"
author = "Ophélia Miralles"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc", "sphinx.ext.autosummary", "sphinx.ext.napoleon"]
templates_path = ["_templates"]
exclude_patterns = []
add_module_names = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_css_files = ["custom.css"]
html_static_path = ["_static"]
html_theme_options = {
    "navbar_align": "content",
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["theme-switcher"],
    "navbar_end": ["search-field.html"],
    "secondary_sidebar_items": ["page-toc"],
}

html_sidebars = {
    "**": ["globaltoc.html", "sourcelink.html"],
    "using/windows": ["windows-sidebar.html"],
}
