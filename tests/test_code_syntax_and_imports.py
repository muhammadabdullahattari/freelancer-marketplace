import importlib
import pkgutil
import pytest
import app


def get_all_app_modules():
    """Recursively collect all module names under app package."""
    modules = []
    for importer, modname, ispkg in pkgutil.walk_packages(app.__path__, prefix="app."):
        modules.append(modname)
    return modules


@pytest.mark.parametrize("module_name", get_all_app_modules())
def test_app_module_imports_cleanly(module_name: str):
    """Verify that every python module in app/ imports cleanly without SyntaxError, ImportError, or NameError."""
    imported_module = importlib.import_module(module_name)
    assert imported_module is not None
