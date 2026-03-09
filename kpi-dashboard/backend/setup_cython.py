"""
Cython build configuration for CS Pulse backend.
Compiles all .py modules to .so shared objects for source protection.

Usage:
    python setup_cython.py build_ext --inplace

After compilation, remove .py source files (keeping entry points):
    find . -name "*.py" ! -name "app_v3_minimal.py" ! -name "__init__.py" ! -name "config.py" ! -name "setup_cython.py" -delete
    find . -name "*.c" -delete  # Remove Cython-generated C files
"""
from setuptools import setup
from Cython.Build import cythonize
import os
import glob


# Files/directories to EXCLUDE from Cython compilation
EXCLUDE_FILES = {
    'setup_cython.py',        # This build script
    'app_v3_minimal.py',      # Flask entry point — must remain .py
    '__init__.py',            # Package markers — must remain .py
    'config.py',              # Runtime configuration
    'conftest.py',            # Pytest config
}

EXCLUDE_DIRS = {
    '__pycache__',
    'tests',
    'test_data',
    'migrations',             # Alembic migrations — keep as .py
    'scripts',                # Data generation scripts — run via subprocess
    'mcp_server',             # MCP server plugins
    'verticals',              # Customer-specific scripts (volume-mounted)
    'templates',              # Jinja/wizard templates
    'agents',                 # Agent scripts (may need source access)
}


def collect_py_files(base_dir):
    """Collect all .py files for Cython compilation, respecting exclusions."""
    py_files = []

    for root, dirs, files in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)

        # Skip excluded directories
        if any(excl in rel_root.split(os.sep) for excl in EXCLUDE_DIRS):
            continue

        for f in files:
            if not f.endswith('.py'):
                continue
            if f in EXCLUDE_FILES:
                continue
            if f.startswith('test_'):
                continue

            full_path = os.path.join(root, f)
            py_files.append(full_path)

    return py_files


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    py_files = collect_py_files(base_dir)

    print(f"Cython: Compiling {len(py_files)} Python files...")
    for f in sorted(py_files):
        print(f"  {os.path.relpath(f, base_dir)}")

    setup(
        name='cspulse-backend',
        ext_modules=cythonize(
            py_files,
            compiler_directives={
                'language_level': '3',
                'boundscheck': False,
                'wraparound': False,
            },
            nthreads=os.cpu_count() or 4,
        ),
        zip_safe=False,
    )
