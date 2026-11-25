"""tools/vendor-kit.sh copies agentfeed and the kit with PINs, and
kit/check_vendor.py notices a vendored copy that was edited."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(repo):
    return subprocess.run([sys.executable, os.path.join(repo, "vendor", "agentviz-kit", "check_vendor.py"), repo],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


@unittest.skipUnless(shutil.which("bash"), "bash not installed")
class VendorKitTest(unittest.TestCase):
    def setUp(self):
        self.viz = tempfile.mkdtemp(prefix="kit-vendor-")
        subprocess.run(["bash", os.path.join(REPO, "tools", "vendor-kit.sh"), self.viz], check=True,
                       stdout=subprocess.DEVNULL)

    def tearDown(self):
        shutil.rmtree(self.viz)

    def test_copies_both_with_pins(self):
        for name, probe in (("agentfeed", "core.py"), ("agentviz-kit", os.path.join("web", "agentviz-wire.js"))):
            self.assertTrue(os.path.isfile(os.path.join(self.viz, "vendor", name, probe)))
            with open(os.path.join(self.viz, "vendor", name, "PIN"), encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(lines[1].startswith("sha256:"))
        result = check(self.viz)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_an_edited_copy_fails(self):
        with open(os.path.join(self.viz, "vendor", "agentfeed", "core.py"), "a", encoding="utf-8") as f:
            f.write("# local edit\n")
        result = check(self.viz)
        self.assertEqual(result.returncode, 1)
        self.assertIn("vendor/agentfeed differs from its PIN", result.stderr)

    def test_served_page_files_must_match(self):
        self.assertTrue(os.path.isfile(os.path.join(self.viz, "web", "agentviz-hud.js")))
        with open(os.path.join(self.viz, "web", "agentviz-hud.js"), "a", encoding="utf-8") as f:
            f.write("// local edit\n")
        self.assertIn("web/agentviz-hud.js differs", check(self.viz).stderr)

    def test_a_missing_pin_fails(self):
        os.remove(os.path.join(self.viz, "vendor", "agentviz-kit", "PIN"))
        self.assertIn("vendor/agentviz-kit: no PIN", check(self.viz).stderr)


if __name__ == "__main__":
    unittest.main()
