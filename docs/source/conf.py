project = "pytest-cocotb"
copyright = "2025, pytest-cocotb contributors"
author = "pytest-cocotb contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pytest": ("https://docs.pytest.org/en/stable", None),
    "cocotb": ("https://docs.cocotb.org/en/stable", None),
}

html_theme = "alabaster"
