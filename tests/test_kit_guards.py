"""kit/tests/guards.py against a throwaway repo: it passes a clean page and
catches each thing it guards against."""
import importlib.util
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("guards", os.path.join(REPO, "kit", "tests", "guards.py"))
guards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guards)


def make_repo(files):
    root = tempfile.mkdtemp(prefix="kit-guards-")
    for name, text in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def run_guards(root):
    class Guards(guards.GuardTests):
        REPO = root
    result = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Guards))
    return len(result.failures) + len(result.errors)


class GuardsTest(unittest.TestCase):
    def test_clean_repo_passes(self):
        root = make_repo({"web/page.js": "try { go(); } catch (e) { console.error(e); }\n",
                          "web/agentviz-hud.js": "el.innerHTML = x;\n",  # vendored: ignored
                          "CLAUDE.md": "cd " + "/" + "root/localci\n",        # allowed file
                          "web/x-engine.js": 'ENV={HOME:"' + "/" + 'home/web_user"}\n'})  # Emscripten's virtual FS
        self.assertEqual(run_guards(root), 0)

    def test_each_problem_is_caught(self):
        self.assertEqual(run_guards(make_repo({"web/page.js": "el.innerHTML = name;\n"})), 1)
        self.assertEqual(run_guards(make_repo({"web/page.js": "try { go(); } catch (e) {}\n"})), 1)
        self.assertEqual(run_guards(make_repo({"web/page.js": "ok\n", "README.md": "NODE_PATH=/" + "root/x\n"})), 1)
        self.assertEqual(run_guards(make_repo({"web/page.js": "ok\n", "web/x-engine.js": "/" + "home/dan/build\n"})), 1)
