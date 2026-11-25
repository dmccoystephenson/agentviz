"""The kit's states and actions are agentfeed's, in the same order: the wire
sends them as indices (kit/web/agentviz-wire.js, kit/scene/agentviz.h)."""
import os
import re
import unittest

from agentfeed.vocabulary import ACTIONS, STATES

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


def js_list(source, name):
    match = re.search(r"const %s = \[([^\]]*)\]" % name, source)
    return tuple(re.findall(r'"([a-z]+)"', match.group(1)))


def cpp_enum(source, name):
    match = re.search(r"enum class %s \{([^}]*)\}" % name, source)
    pairs = re.findall(r"(\w+) = (\d+)", match.group(1))
    return tuple(word.lower() for word, index in sorted(pairs, key=lambda p: int(p[1])))


class KitVocabularyTest(unittest.TestCase):
    def test_wire_js_matches(self):
        source = read("kit", "web", "agentviz-wire.js")
        self.assertEqual(js_list(source, "STATES"), STATES)
        self.assertEqual(js_list(source, "ACTIONS"), ACTIONS)

    def test_header_matches(self):
        source = read("kit", "scene", "agentviz.h")
        self.assertEqual(cpp_enum(source, "State"), STATES)
        self.assertEqual(cpp_enum(source, "Action"), ACTIONS)


if __name__ == "__main__":
    unittest.main()
