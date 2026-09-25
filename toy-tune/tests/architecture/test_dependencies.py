import ast
from pathlib import Path
import unittest

PACKAGE = Path(__file__).resolve().parents[2] / "src/toy_tune"


class ArchitectureTests(unittest.TestCase):
    def test_inner_layers_only_import_declared_core_dependencies(self):
        standard = {"dataclasses", "hashlib", "re", "typing", "json"}
        for layer in ("domain", "application"):
            for path in (PACKAGE / layer).rglob("*.py"):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    modules = []
                    if isinstance(node, ast.Import):
                        modules = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        self.assertEqual(node.level, 0, f"Use explicit absolute imports: {path}")
                        modules = [node.module or ""]
                    for module in modules:
                        internal = module.startswith("toy_tune.domain")
                        if layer == "application":
                            internal = internal or module.startswith("toy_tune.application")
                        self.assertTrue(internal or module in standard, f"Forbidden dependency {module} in {path}")
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, {"open", "__import__", "eval", "exec"}, str(path))
