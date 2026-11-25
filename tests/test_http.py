"""The local server: static files, the feed, and what it refuses."""
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentfeed.adapters.http_server import is_local_host, make_handler  # noqa: E402

PORT = int(os.environ.get("AGENTVIZ_TEST_PORT", "8940"))


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.web = os.path.join(cls.tmp.name, "web")
        os.makedirs(cls.web)
        with open(os.path.join(cls.web, "index.html"), "w") as f:
            f.write("ok")
        with open(os.path.join(cls.tmp.name, "secret.txt"), "w") as f:
            f.write("outside")
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(cls.web, True))
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def get(self, path, host="127.0.0.1:%d" % PORT):
        connection = http.client.HTTPConnection("127.0.0.1", PORT)
        connection.putrequest("GET", path, skip_host=True)
        connection.putheader("Host", host)
        connection.endheaders()
        response = connection.getresponse()
        return response.status, response.read()

    def test_page_and_feed(self):
        self.assertEqual(self.get("/"), (200, b"ok"))
        status, body = self.get("/api/agents")
        self.assertEqual((status, json.loads(body)["fixture"]), (200, True))

    def test_no_path_outside_web_dir(self):
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt"):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_refuses_foreign_host(self):
        self.assertEqual(self.get("/api/agents", host="attacker.example:%d" % PORT)[0], 403)
        self.assertEqual(self.get("/", host="localhost:%d" % PORT)[0], 200)

    def test_is_local_host(self):
        self.assertTrue(is_local_host("127.0.0.1:8841"))
        self.assertTrue(is_local_host("[::1]:8841"))
        self.assertFalse(is_local_host("127.0.0.1.attacker.example"))
        self.assertFalse(is_local_host(None))
