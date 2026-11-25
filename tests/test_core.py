"""The pure core, driven through fake ports: no files, processes or clock."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentfeed import build_feed_from, core  # noqa: E402
from agentfeed.model import Activity, Follower, History, SessionRecord, ToolCall  # noqa: E402
from agentfeed.ports import ActivitySource, SessionSource  # noqa: E402

NOW = 1_000_000.0


class FakeSessions(SessionSource):
    def __init__(self, records):
        self.records = records

    def sessions(self, now):
        return self.records


class FakeActivity(ActivitySource):
    def __init__(self, by_id):
        self.by_id = by_id

    def activity(self, record, now):
        return self.by_id.get(record.raw["sessionId"])


def record(session_id, status="busy", alive=True, **raw):
    return SessionRecord(raw=dict(sessionId=session_id, status=status, cwd="/w/" + session_id,
                                  startedAt=1, updatedAt=NOW * 1000, **raw), alive=alive)


class Summarize(unittest.TestCase):
    def test_current_and_recent_calls(self):
        history = History(tools=[ToolCall("Read", "a.py", NOW - 30), ToolCall("Edit", "b.py", NOW - 2)],
                          branch="main")
        activity = core.summarize(history, NOW)
        self.assertEqual(activity.current, {"tool": "Edit", "action": "edit", "label": "b.py", "ageSec": 2.0})
        self.assertEqual([c["action"] for c in activity.recent], ["read", "edit"])
        self.assertEqual(activity.branch, "main")

    def test_followers_sorted_and_capped(self):
        followers = [Follower("f%d" % i, "lane %d" % i, quiet_sec=i * 100.0, tools=[ToolCall("Grep", None, NOW - 1)])
                     for i in range(10, 0, -1)]
        entries = core.summarize_followers(followers, NOW)
        self.assertEqual(len(entries), 8)
        self.assertEqual(entries[0]["label"], "lane 1")
        self.assertEqual(entries[0]["state"], "active")
        self.assertEqual(entries[1]["state"], "resting")
        self.assertEqual(entries[1]["action"], "none")


class Document(unittest.TestCase):
    def test_states_actions_and_places(self):
        sessions = FakeSessions([record("a"), record("b", status="waiting"), record("c", alive=False)])
        activity = FakeActivity({"a": Activity(current={"tool": "Bash", "action": "run", "label": None, "ageSec": 4.0},
                                               followers=[{"id": "x", "state": "active"}])})
        doc = build_feed_from(sessions, activity, NOW)
        by_id = {s["id"]: s for s in doc["sessions"]}
        self.assertEqual(by_id["a"]["action"], "run")
        self.assertEqual(by_id["b"]["state"], "waiting")
        self.assertEqual(by_id["c"]["state"], "offline")
        self.assertEqual(doc["counts"]["activeFollowers"], 1)
        self.assertEqual({p["id"] for p in doc["places"]}, {"a", "b", "c"})

    def test_delegating_when_quiet_with_active_followers(self):
        activity = FakeActivity({"a": Activity(current={"tool": "Agent", "action": "delegate", "ageSec": 500.0},
                                               followers=[{"id": "x", "state": "active"}])})
        doc = build_feed_from(FakeSessions([record("a")]), activity, NOW)
        self.assertEqual(doc["sessions"][0]["action"], "delegate")

    def test_offline_window(self):
        old = record("old", alive=False, )
        old.raw["updatedAt"] = (NOW - 10 * 3600) * 1000
        doc = build_feed_from(FakeSessions([old, record("new", alive=False)]), FakeActivity({}), NOW)
        self.assertEqual([s["id"] for s in doc["sessions"]], ["new"])
        everything = build_feed_from(FakeSessions([old]), FakeActivity({}), NOW, offline_window_sec=None)
        self.assertEqual(len(everything["sessions"]), 1)

    def test_stalled(self):
        stale = record("s")
        stale.raw["updatedAt"] = (NOW - 900) * 1000
        doc = build_feed_from(FakeSessions([stale]), FakeActivity({}), NOW)
        self.assertTrue(doc["sessions"][0]["stalled"])


class NewFields(unittest.TestCase):
    """Fields added in agentfeed 0.3 (schema v1, additive)."""

    def test_waiting_reason_and_seconds(self):
        asking = record("q", status="waiting", statusUpdatedAt=(NOW - 40) * 1000)
        blocked = record("p", status="waiting", statusUpdatedAt=(NOW - 90) * 1000)
        activity = FakeActivity({"q": Activity(current={"tool": "AskUserQuestion", "action": "other", "ageSec": 40.0}),
                                 "p": Activity(current={"tool": "Bash", "action": "run", "ageSec": 90.0})})
        by_id = {s["id"]: s for s in build_feed_from(FakeSessions([asking, blocked, record("b")]), activity,
                                                     NOW)["sessions"]}
        self.assertEqual((by_id["q"]["waitingReason"], by_id["q"]["waitingSec"]), ("question", 40.0))
        self.assertEqual((by_id["p"]["waitingReason"], by_id["p"]["waitingSec"]), ("permission", 90.0))
        self.assertEqual((by_id["b"]["waitingReason"], by_id["b"]["waitingSec"]), (None, None))

    def test_tool_counts_and_last_call(self):
        history = History(tools=[ToolCall("Read", None, NOW - 9), ToolCall("Edit", None, NOW - 3)],
                          followers=[Follower("f", "lane", 2.0, [ToolCall("Grep", None, NOW - 2)] * 5)])
        doc = build_feed_from(FakeSessions([record("a")]), FakeActivity({"a": core.summarize(history, NOW)}), NOW)
        session = doc["sessions"][0]
        self.assertEqual((session["toolCount"], session["lastToolAt"]), (2, NOW - 3))
        self.assertEqual(doc["places"][0]["toolCount"], 7)

    def test_follower_stalled_needs_unfinished_and_quiet(self):
        self.assertTrue(core.follower_stalled(False, 400))
        self.assertFalse(core.follower_stalled(False, 100))
        self.assertFalse(core.follower_stalled(True, 800))
        self.assertFalse(core.follower_stalled(None, 800))

    def test_follower_branch_finished_started(self):
        follower = Follower("f", "lane", 400.0, [ToolCall("Bash", None, NOW - 400)], finished=False,
                            started_at=NOW - 1000, branch="fix/x")
        entry = core.summarize_followers([follower], NOW)[0]
        self.assertEqual((entry["finished"], entry["stalled"], entry["branch"], entry["startedAt"]),
                         (False, True, "fix/x", NOW - 1000))


class Hardening(unittest.TestCase):
    def test_malformed_registry_fields_do_not_break_the_feed(self):
        broken = [SessionRecord({"sessionId": "a", "startedAt": "yesterday", "status": ["x"], "kind": 3,
                                 "name": {"n": 1}}, True),
                  record("b")]
        doc = build_feed_from(FakeSessions(broken), FakeActivity({}), NOW)
        by_id = {s["id"]: s for s in doc["sessions"]}
        self.assertEqual((by_id["a"]["startedAt"], by_id["a"]["status"], by_id["a"]["state"], by_id["a"]["kind"]),
                         (0, None, "dim", None))
        self.assertEqual(by_id["a"]["name"], "home-a")


class Redaction(unittest.TestCase):
    def test_token_shaped_strings_are_redacted(self):
        from agentfeed.labels import short_label, tool_label
        cases = {
            "curl -H 'Authorization: Bearer sk-ant-abcdef123456' https://x": "sk-ant",
            "Push with ghp_abcdefghijklmnop1234": "ghp_",
            "Export API_KEY=hunter2hunter2": "hunter2",
            "Use key AKIAABCDEFGHIJKLMNOP": "AKIA",
            "Check digest 0123456789abcdef0123456789abcdef": "0123456789abcdef0123",
        }
        for text, secret in cases.items():
            label = tool_label("Bash", {"description": text})
            self.assertNotIn(secret, label, text)
            self.assertIn("[redacted]", label, text)
        self.assertEqual(short_label("Run the test suite"), "Run the test suite")
        self.assertEqual(tool_label("Read", {"file_path": "/w/test_architecture_layering_enforcement.py"}),
                         "test_architecture_layering_enforcement.py")


class Hardening032(unittest.TestCase):
    """From the public-readiness re-review (code lane)."""

    def test_non_finite_and_oversized_registry_fields(self):
        import json
        raw = {"sessionId": "x" * 500, "startedAt": float("inf"), "status": "s" * 5000, "kind": "k" * 5000}
        doc = build_feed_from(FakeSessions([SessionRecord(raw, True)]), FakeActivity({}), NOW)
        json.dumps(doc, allow_nan=False)  # raises on NaN / Infinity
        session = doc["sessions"][0]
        self.assertEqual(session["startedAt"], 0)
        self.assertLessEqual(len(session["id"]), 80)
        self.assertLessEqual(len(session["status"]), 32)
        self.assertLessEqual(len(session["kind"]), 32)

    def test_more_secret_shapes_are_redacted(self):
        from agentfeed.labels import tool_label
        cases = {
            "Use sk_live_abcdefghijklmnop": "sk_live_abc",
            "Token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJl": "eyJhbGci",
            "curl https://user:hunter2pass@x.io/p": "hunter2pass",
            "Run with PGPASSWORD=s3cr3t psql": "s3cr3t",
            "GH_TOKEN=abcdef gh pr list": "abcdef",
            "Call --token abc123def456": "abc123def456",
            "Key AIzaSyA1234567890abcdefghij": "AIzaSy",
            "Push with glpat-abcdefghijklmnopqrst": "glpat-",
            "Publish npm_abcdefghijklmnopqrstuvwxyz12": "npm_abc",
            "Paste -----BEGIN RSA PRIVATE KEY-----": "PRIVATE KEY",
            "Set api key: abcdef123": "abcdef123",
        }
        for text, secret in cases.items():
            label = tool_label("Bash", {"description": text})
            self.assertNotIn(secret, label, text)
        for ordinary in ("Run the test suite", "Check lane PRs", "Rebuild the token list UI"):
            self.assertEqual(tool_label("Bash", {"description": ordinary}), ordinary)

    def test_web_host_never_carries_userinfo(self):
        from agentfeed.labels import tool_label
        self.assertEqual(tool_label("WebFetch", {"url": "https://user:pw@internal.corp/x"}), "internal.corp")
        self.assertEqual(tool_label("WebFetch", {"url": "https://example.com:8443/p?q=1"}), "example.com")
        self.assertIsNone(tool_label("WebFetch", {"url": "file:///etc/passwd"}))
