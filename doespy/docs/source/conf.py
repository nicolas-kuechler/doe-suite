import os
import sys

#sys.path.insert(0, os.path.abspath('../doespy/etl/steps'))
sys.path.append(os.path.abspath('../doespy/etl/steps'))
sys.path.append(os.path.abspath('..'))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DoES'
copyright = '2022, Nicolas Kuechler'
author = 'Nicolas Kuechler'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

#extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode", 'sphinxemoji.sphinxemoji', 'sphinx.ext.autosectionlabel', 'enum_tools.autoenum', 'sphinxcontrib.autodoc_pydantic', 'sphinx.ext.napoleon'] #,
extensions = ["sphinx.ext.viewcode", 'sphinxemoji.sphinxemoji', 'sphinxcontrib.autodoc_pydantic', "sphinx.ext.autosectionlabel", 'enum_tools.autoenum'] #,

numpydoc_show_class_members = False

python_use_unqualified_type_names = True
#autodoc_unqualified_typehints = True
#autodoc_typehints = "description"

autodoc_class_signature = "separated"
autodoc_member_order = 'bysource'

autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_json = False
autodoc_pydantic_settings_show_json = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_summary_list_order = "bysource"
autodoc_pydantic_settings_summary_list_order = "bysource"
autodoc_pydantic_model_member_order = "bysource"
autodoc_pydantic_field_show_alias = False
autodoc_pydantic_field_show_default = True
autodoc_pydantic_field_swap_name_and_alias = True

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

html_css_files = [
    'css/custom.css',
]