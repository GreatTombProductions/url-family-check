"""Local-only checks. No address outside this process is contacted."""

import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check


HITS = []
SEEN_AUTH = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        HITS.append(self.path)
        SEEN_AUTH.append(self.headers.get("Authorization"))
        if self.path == "/go":
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{self.server.server_address[1]}/ok")
            self.end_headers()
            return
        if self.path == "/no":
            self.send_response(401)
            self.end_headers()
            return
        if self.path == "/stop":
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"page")

    def log_message(self, fmt, *args):
        return


def serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_verdicts():
    assert check.verdict(302) == "redirect"
    assert check.verdict(307) == "redirect"
    assert check.verdict(401) == "challenged"
    assert check.verdict(403) == "refused"
    assert check.verdict(200) == "served"
    assert check.verdict(204) == "served"
    assert check.verdict(404) == "other"
    assert check.verdict(500) == "other"


def test_refuses_credentials_and_other_schemes():
    for bad in ("ftp://example.com/", "https://alice:pw@localhost/a", "not a url", ""):
        try:
            check.normalize(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def test_local_server_does_not_follow_or_send_authorization():
    HITS.clear()
    SEEN_AUTH.clear()
    server = serve()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        redirect = check.probe(base + "/go")
        challenged = check.probe(base + "/no")
        refused = check.probe(base + "/stop")
        served = check.probe(base + "/ok")
    finally:
        server.shutdown()
    assert redirect["status"] == 302 and redirect["verdict"] == "redirect"
    assert redirect["location"].endswith("/ok")
    assert challenged["verdict"] == "challenged"
    assert refused["verdict"] == "refused"
    assert served["verdict"] == "served"
    assert HITS.count("/go") == 1
    assert "/ok" in HITS  # only the direct /ok request, not a followed redirect
    assert HITS.count("/ok") == 1
    assert SEEN_AUTH == [None, None, None, None]


def test_main_reports_a_bad_address_without_raising():
    code = check.main(["ftp://example.com/file"])
    assert code == 1


if __name__ == "__main__":
    test_verdicts()
    test_refuses_credentials_and_other_schemes()
    test_local_server_does_not_follow_or_send_authorization()
    test_main_reports_a_bad_address_without_raising()
    print("ok")
