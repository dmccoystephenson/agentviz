"""The layering rules: the core and the ports never touch the outside world,
and nothing in the core depends on an adapter."""
import ast
import os
import unittest

PACKAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agentfeed")
PURE = ["core.py", "model.py", "vocabulary.py", "labels.py", "times.py",
        "ports/__init__.py", "ports/session_source.py", "ports/activity_source.py"]
IO_MODULES = {"glob", "socket", "subprocess", "threading", "http", "urllib", "shutil", "json"}


def imports_of(path):
    tree = ast.parse(open(path).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, 0
        elif isinstance(node, ast.ImportFrom):
            yield node.module or "", node.level


class Layering(unittest.TestCase):
    def test_pure_modules_do_no_io(self):
        for name in PURE:
            for module, level in imports_of(os.path.join(PACKAGE, name)):
                if level == 0:
                    self.assertNotIn(module.split(".")[0], IO_MODULES, "%s imports %s" % (name, module))

    def test_pure_modules_never_import_adapters_or_service(self):
        for name in PURE:
            for module, level in imports_of(os.path.join(PACKAGE, name)):
                if level:
                    self.assertFalse(module.startswith(("adapters", "service")), "%s imports %s" % (name, module))

    def test_one_file_per_port_and_adapter(self):
        ports = sorted(f for f in os.listdir(os.path.join(PACKAGE, "ports")) if f.endswith(".py") and f != "__init__.py")
        self.assertEqual(ports, ["activity_source.py", "session_source.py"])
