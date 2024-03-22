# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Instrument-To-Instrument'
copyright = '2024, Christoph Schirninger, Robert Jarolim, J. Emmanuel Johnson, Anna Jungbluth, Lilli Freischem, Anne Spalding'
author = 'Christoph Schirninger, Robert Jarolim, J. Emmanuel Johnson, Anna Jungbluth, Lilli Freischem, Anne Spalding'
release = '0.1.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
]

templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'alabaster'
html_theme = 'sphinxdoc'
html_static_path = ['_static']
