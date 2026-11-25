"""kit/scene/agentviz.h, compiled natively with g++: seed_of matches
agentfeed's, and it decodes the buffer kit/web/agentviz-wire.js packed
(tests/kit/wire_fixture.f32, from tests/kit/wire_fixture.json)."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from agentfeed.labels import seed_of
from agentfeed.vocabulary import ACTIONS, STATES

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(REPO, "tests", "kit")
STRINGS = ["demo-lead", "a", "site-one", "démo-ü-✓-\U0001f98a", "plugin-site/demo-b1"]


def fnv1a(text):
    value = 2166136261
    for character in text:
        value = ((value ^ ord(character)) * 16777619) & 0xFFFFFFFF
    return value


@unittest.skipUnless(shutil.which("g++"), "g++ not installed")
class NativeHeaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="kit-native-")
        binary = os.path.join(cls.tmp, "agentviz_test")
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(REPO, "kit", "scene"),
                        os.path.join(KIT, "agentviz_test.cpp"), "-o", binary], check=True)
        out = subprocess.run([binary, os.path.join(KIT, "wire_fixture.f32")] + STRINGS,
                             check=True, stdout=subprocess.PIPE).stdout
        cls.result = json.loads(out.decode("utf-8"))
        with open(os.path.join(KIT, "wire_fixture.json"), encoding="utf-8") as f:
            cls.spec = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_seed_of_matches_python(self):
        for text, (hashed, seed) in zip(STRINGS, self.result["seeds"]):
            self.assertEqual(hashed, fnv1a(text), text)
            self.assertAlmostEqual(seed, seed_of(text), places=4, msg=text)

    def test_header(self):
        frame = self.result["frame"]
        self.assertTrue(frame["ok"])
        self.assertEqual(frame["waitingCount"], 1)
        self.assertEqual(frame["fixture"], 1)
        self.assertEqual((frame["scene0"], frame["scene15"]), (1.0, 16.0))
        self.assertTrue(self.result["refusesTruncated"])

    def test_zone_and_link(self):
        zone, link = self.result["frame"]["zones"][0], self.result["frame"]["links"][0]
        self.assertEqual(zone["id"], fnv1a("site-one") & 0xFFFFFF)
        self.assertEqual((zone["kind"], zone["seed"], zone["x0"], zone["z1"], zone["appear"], zone["extra0"]),
                         (2, 0.125, -1.0, 4.0, 0.5, 0.25))
        self.assertEqual(link["from"], fnv1a("demo-lead") & 0xFFFFFF)
        self.assertEqual(link["to"], fnv1a("demo-lead/f-one") & 0xFFFFFF)
        self.assertEqual((link["kind"], link["y1"], link["alpha"]), (1, 4.0, 0.75))

    def test_agents(self):
        lead, active, resting, waiting = self.result["frame"]["agents"]
        sessions = self.spec["doc"]["sessions"]
        self.assertEqual(lead["id"], fnv1a("demo-lead") & 0xFFFFFF)
        self.assertEqual((lead["kind"], lead["state"], lead["action"]), (0, STATES.index("busy"), ACTIONS.index("run")))
        self.assertEqual((lead["x"], lead["y"], lead["z"], lead["facing"]), (1.0, 2.0, 3.0, 1.5))
        self.assertEqual((lead["highlight"], lead["pulse"], lead["toolCount"], lead["activeFollowers"]), (1, 0.5, 12, 1))
        self.assertEqual(lead["extra0"], 7.0)
        self.assertEqual((active["kind"], active["state"], active["action"]), (1, STATES.index("busy"), ACTIONS.index("edit")))
        self.assertEqual((active["parent"], active["parentSeed"], active["appear"]), (lead["id"], 0.25, 0.25))
        self.assertEqual((resting["state"], resting["action"], resting["stalled"]), (STATES.index("idle"), 0, 1))
        self.assertEqual(waiting["id"], fnv1a(sessions[1]["id"]) & 0xFFFFFF)
        self.assertEqual((waiting["state"], waiting["waitingReason"]), (STATES.index("waiting"), 2))
        self.assertAlmostEqual(waiting["seed"], seed_of(sessions[1]["id"]), places=4)
        self.assertEqual((waiting["highlight"], waiting["extra15"]), (2, 99.0))


if __name__ == "__main__":
    unittest.main()
