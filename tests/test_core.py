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
