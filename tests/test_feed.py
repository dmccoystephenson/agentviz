import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentfeed import feed  # noqa: E402
from agentfeed.serve import FIXTURE_FILE  # noqa: E402


class FixtureFeed(unittest.TestCase):
    def setUp(self):
        self.doc = feed.build_feed(fixture=feed.load_fixture(FIXTURE_FILE), now=time.time())

    def test_schema(self):
        self.assertEqual(self.doc["version"], 1)
        self.assertTrue(self.doc["fixture"])
        for s in self.doc["sessions"]:
            for k in ("id", "name", "state", "action", "place", "followers", "seed"):
                self.assertIn(k, s)
            self.assertIn(s["state"], feed.STATES)
            self.assertIn(s["action"], feed.ACTIONS)
            for f in s["followers"]:
                self.assertIn(f["state"], ("active", "resting"))
                self.assertIn(f["action"], feed.ACTIONS)

    def test_every_state_present(self):
        states = {s["state"] for s in self.doc["sessions"]}
        self.assertTrue({"offline", "idle", "busy", "waiting"} <= states)

    def test_every_action_present(self):
        actions = {s["action"] for s in self.doc["sessions"]}
        self.assertTrue({"edit", "read", "web", "delegate", "think", "other"} <= actions)

    def test_no_drift(self):
        """The same fixture gives the same states an hour later."""
        later = feed.build_feed(fixture=feed.load_fixture(FIXTURE_FILE), now=time.time() + 3600)
        key = lambda d: [(s["id"], s["state"], s["action"], s["stalled"]) for s in d["sessions"]]
        self.assertEqual(key(self.doc), key(later))
        stalled = [s["name"] for s in self.doc["sessions"] if s["stalled"]]
        self.assertEqual(stalled, ["Patch"])

    def test_counts(self):
        c = self.doc["counts"]
        self.assertEqual(c["followers"], sum(len(s["followers"]) for s in self.doc["sessions"]))


class Mappings(unittest.TestCase):
    def test_actions(self):
        self.assertEqual(feed.action_of_tool("Edit"), "edit")
        self.assertEqual(feed.action_of_tool("Bash"), "run")
        self.assertEqual(feed.action_of_tool("Agent"), "delegate")
        self.assertEqual(feed.action_of_tool("mcp__x"), "other")
        self.assertEqual(feed.current_action("busy", "Edit", 500, followers=2), "delegate")
        self.assertEqual(feed.current_action("busy", "Edit", 500), "think")
        self.assertEqual(feed.current_action("idle", "Edit", 1), "none")

    def test_labels_hold_no_content(self):
        self.assertEqual(feed.tool_label("Edit", {"file_path": "/secret/dir/a.py", "new_string": "x"}), "a.py")
        self.assertIsNone(feed.tool_label("Bash", {"command": "cat /etc/passwd"}))
        self.assertEqual(feed.tool_label("WebFetch", {"url": "https://example.com/p?q=1"}), "example.com")

    def test_seed_matches_village(self):
        self.assertEqual(feed.seed_of("~"), feed.seed_of("~"))
        self.assertTrue(0 <= feed.seed_of("abc") < 1)


class LiveFromDisk(unittest.TestCase):
    """A throwaway ~/.claude with one session, a transcript and a subagent."""

    def test_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            sessions = os.path.join(tmp, "sessions")
            projects = os.path.join(tmp, "projects")
            os.makedirs(sessions)
            cwd = "/work/repo-x"
            pdir = os.path.join(projects, feed.encode_cwd(cwd))
            os.makedirs(os.path.join(pdir, "sid1", "subagents"))
            now = time.time()
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 5))
            with open(os.path.join(sessions, "1.json"), "w") as f:
                json.dump({"pid": os.getpid(), "sessionId": "sid1", "cwd": cwd, "status": "busy",
                           "name": "Tester", "updatedAt": now * 1000, "startedAt": now * 1000 - 1}, f)
            line = {"type": "assistant", "timestamp": ts, "gitBranch": "feat/x",
                    "message": {"content": [{"type": "tool_use", "name": "Edit",
                                             "input": {"file_path": "/work/repo-x/main.cpp", "new_string": "SECRET"}}]}}
            with open(os.path.join(pdir, "sid1.jsonl"), "w") as f:
                f.write(json.dumps(line) + "\n")
            sub = os.path.join(pdir, "sid1", "subagents", "agent-abc.jsonl")
            with open(sub, "w") as f:
                f.write(json.dumps({**line, "message": {"content": [{"type": "tool_use", "name": "Grep", "input": {}}]}}) + "\n")
            with open(sub[:-6] + ".meta.json", "w") as f:
                json.dump({"description": "lane a"}, f)
            # The test process is python, not claude: inject the liveness check.
            doc = feed.build_feed(sessions, projects, now=now, is_alive=lambda pid: True)
            self.assertEqual(len(doc["sessions"]), 1)
            s = doc["sessions"][0]
            self.assertEqual((s["state"], s["action"], s["branch"], s["place"]), ("busy", "edit", "feat/x", "repo-x"))
            self.assertEqual(s["activity"]["label"], "main.cpp")
            self.assertEqual([f["label"] for f in s["followers"]], ["lane a"])
            self.assertNotIn("SECRET", json.dumps(doc))
            self.assertNotIn("/work", json.dumps(doc))


if __name__ == "__main__":
    unittest.main()
