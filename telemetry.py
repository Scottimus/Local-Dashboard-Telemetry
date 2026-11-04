"""Small localhost HTTP service extracted from a larger dashboard integration."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import platform
import subprocess
import threading
import time


def number(value):
    try:
        return round(float(value), 2)
    except ValueError:
        return None


def gpu_snapshot():
    query = "name,utilization.gpu,power.draw,power.limit,temperature.gpu,memory.used,memory.total"
    result = subprocess.run(["nvidia-smi", "--query-gpu=" + query, "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, check=True, timeout=5)
    first = result.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in first.split(",")]
    if len(parts) != 7:
        raise ValueError("Unexpected GPU response")
    used, total = number(parts[5]), number(parts[6])
    return {"name": parts[0], "utilization": number(parts[1]), "powerDraw": number(parts[2]),
            "powerLimit": number(parts[3]), "temperature": number(parts[4]),
            "memoryUsedMiB": used, "memoryTotalMiB": total,
            "memoryUsedPercent": round(used / total * 100, 2) if used is not None and total else None}


def system_snapshot():
    import psutil
    memory = psutil.virtual_memory()
    return {"platform": platform.system(), "cpuCount": os.cpu_count(),
            "cpuPercent": psutil.cpu_percent(interval=0.05), "memoryUsedPercent": memory.percent,
            "memoryTotalMiB": round(memory.total / 1024 ** 2)}


class Snapshots:
    def __init__(self, sample=False, ttl=2):
        self.sample = sample
        self.ttl = ttl
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, name):
        with self.lock:
            now = time.monotonic()
            previous = self.cache.get(name)
            if previous and now - previous[0] < self.ttl:
                return 200, {"cached": True, "sample": self.sample, "data": previous[1]}
            try:
                if self.sample:
                    data = json.loads((Path(__file__).parent / "examples/snapshot.json").read_text())[name]
                else:
                    data = {"gpu": gpu_snapshot, "system": system_snapshot}[name]()
            except (OSError, ValueError, IndexError, subprocess.SubprocessError, ImportError):
                return 503, {"cached": False, "sample": self.sample, "error": "sensor_unavailable"}
            self.cache[name] = (now, data)
            return 200, {"cached": False, "sample": self.sample, "data": data}


def handler_for(snapshots):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/":
                body = (Path(__file__).parent / "index.html").read_bytes()
                status, content_type = 200, "text/html; charset=utf-8"
            else:
                if path == "/health":
                    status, data = 200, {"status": "ok", "sample": snapshots.sample}
                elif path in {"/api/gpu", "/api/system"}:
                    status, data = snapshots.get(path.rsplit("/", 1)[1])
                else:
                    status, data = 404, {"error": "not_found"}
                body = json.dumps(data).encode()
                content_type = "application/json"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass
    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(Snapshots(sample=args.sample)))
    print(f"Dashboard available at http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
