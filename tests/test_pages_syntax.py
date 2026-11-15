"""
Syntax and AST validation tests for Streamlit application pages and core modules.
Verifies that all pages, utilities, components, and database modules compile cleanly.
"""

from __future__ import annotations

import ast
import os
import py_compile

import pytest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_python_files():
    """Discover all Python source files in the project workspace."""
    py_files = []
    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # Exclude hidden directories, caches, virtual environments
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__" and d != "venv"]
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files


@pytest.mark.parametrize("file_path", get_all_python_files())
def test_python_file_ast_validity(file_path):
    """Verify that every python file can be parsed into an Abstract Syntax Tree."""
    rel_path = os.path.relpath(file_path, WORKSPACE_ROOT)
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
    
    # Must parse without syntax errors
    tree = ast.parse(source_code, filename=rel_path)
    assert tree is not None, f"Failed to parse AST for {rel_path}"


@pytest.mark.parametrize("file_path", get_all_python_files())
def test_python_file_compilation(file_path):
    """Verify that every python file compiles to bytecode with py_compile."""
    rel_path = os.path.relpath(file_path, WORKSPACE_ROOT)
    compiled = py_compile.compile(file_path, doraise=True)
    assert compiled is not None, f"Compilation failed for {rel_path}"
