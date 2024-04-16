import os
import sys

#sys.path.insert(0, os.path.abspath('../doespy/etl/steps'))
sys.path.append(os.path.abspath('../../doespy/etl/steps'))
sys.path.append(os.path.abspath('../..'))

sys.path.append(os.path.abspath("./ext"))


sys.path.append(os.path.join(os.environ["DOES_PROJECT_DIR"], "doe-suite-config"))

# needs manual import to prevent circular import
from doespy.design.etl_design import MyETLBaseModel


#sys.path.insert(0, os.path.abspath('../..'))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DoE-Suite'
copyright = '2022, Nicolas Kuechler'
author = 'Nicolas Kuechler'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

#extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode", 'sphinxemoji.sphinxemoji', 'sphinx.ext.autosectionlabel', 'enum_tools.autoenum', 'sphinxcontrib.autodoc_pydantic', 'sphinx.ext.napoleon'] #, # "sphinxcontrib.autoyaml"
extensions = [
    "sphinx_copybutton", # adds a copy button to code blocks
    "sphinx.ext.extlinks", # allows simplified links, see `extlinks` below
    "sphinx.ext.todo",
    "sphinx_tabs.tabs",
    "sphinx_toolbox.collapse",
    "sphinxcontrib.programoutput",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    'sphinxemoji.sphinxemoji',
    'sphinxcontrib.autodoc_pydantic',
    "sphinx.ext.autosectionlabel",
    'enum_tools.autoenum'] #,

myautoyaml_root = "../.."
myautoyaml_doc_delimiter = "###"

todo_include_todos = True


numpydoc_show_class_members = False

python_use_unqualified_type_names = True
#autodoc_unqualified_typehints = True
#autodoc_typehints = "description"

extlinks = {
    'repodir': ('https://github.com/nicolas-kuechler/doe-suite/tree/main/%s', '%s')
}

autodoc_class_signature = "separated"
autodoc_member_order = 'bysource'

autosectionlabel_prefix_document = True

autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_field_list_validators = False
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

html_theme_options = {
    "page_width":  "1440px", # "1280px", #"940px"
    "fixed_sidebar": True,
}

html_css_files = [
    'css/custom.css',
]