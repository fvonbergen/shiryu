# noqa: D100
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'shiryu'  # fmt: skip
copyright = "2025, 'von Bergen, Federico'"  # noqa: A001
author = "'von Bergen, Federico'"

from importlib.metadata import version as _version  # noqa: E402

release = _version('shiryu')  # fmt: skip
version = '.'.join(release.split('.')[:2])  # fmt: skip

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.imgmath',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]  # fmt: skip

templates_path = ['_templates']  # fmt: skip
exclude_patterns = []

language = 'en'  # fmt: skip

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
# TODO: check that sphinx_rtd_theme is installed
html_theme = 'sphinx_rtd_theme'  # fmt: skip
html_static_path = ['_static']  # fmt: skip

# -- Options for intersphinx extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}  # fmt: skip

# -- Options for autodoc extension ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#configuration


# sphinx-autodoc-typehints settings.
typehints_defaults = 'comma'  # fmt: skip


# -- Options for todo extension ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/todo.html#configuration

todo_include_todos = True
