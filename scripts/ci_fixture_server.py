"""TEST ONLY: Moto S3 and a deterministic model protocol fixture; neither is a production provider."""

import json
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ModelFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/cluster":
            try:
                with urllib.request.urlopen("http://spark-master:8081/json/", timeout=3) as source:
                    state = json.load(source)
                body = json.dumps(
                    {
                        "alive_workers": state.get("aliveworkers", 0),
                        "active_application_names": [item["name"] for item in state.get("activeapps", [])],
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_response(503)
                self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"fixture-ready")

    def do_POST(self):
        data = json.loads(self.rfile.read(min(65536, int(self.headers.get("Content-Length", 0)))))
        instruction = json.loads(data["messages"][-1]["content"])
        operation = instruction["operation"]
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}\b"
        group, steps = 0, []
        if operation == "regex_extract":
            pattern = r"ORD-\d+"
        elif operation == "normalize":
            pattern = None
            steps = ["trim", "collapse_whitespace", "lowercase"]
        plan = {
            "operation": operation,
            "pattern": pattern,
            "group": group,
            "steps": steps,
            "explanation": "Deterministic CI fixture: not a real model response.",
        }
        body = json.dumps(
            {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(plan)}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    moto = subprocess.Popen(
        [sys.executable, "-m", "moto.server", "-H", "0.0.0.0", "-p", "5000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ThreadingHTTPServer(("0.0.0.0", 8009), ModelFixture).serve_forever()
    finally:
        moto.terminate()
        moto.wait(timeout=10)
