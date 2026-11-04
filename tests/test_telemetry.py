from http.server import ThreadingHTTPServer
import json
import subprocess
import threading
import unittest
from unittest.mock import patch
import urllib.request
from telemetry import Snapshots, handler_for


class TelemetryTests(unittest.TestCase):
    def test_cache_and_timeout(self):
        snapshots = Snapshots()
        with patch("telemetry.gpu_snapshot", return_value={"name": "test"}) as builder:
            self.assertFalse(snapshots.get("gpu")[1]["cached"])
            self.assertTrue(snapshots.get("gpu")[1]["cached"])
            self.assertEqual(builder.call_count, 1)
        with patch("telemetry.gpu_snapshot", side_effect=subprocess.TimeoutExpired("sensor", 5)):
            self.assertEqual(Snapshots().get("gpu")[0], 503)

    def test_http_sample_endpoints(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(Snapshots(sample=True)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for route in ("/health", "/api/gpu", "/api/system"):
                with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}" + route) as response:
                    self.assertTrue(json.load(response)["sample"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
