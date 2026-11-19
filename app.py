import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from settings import Settings


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        settings = self.server.settings
        path = self.path.partition("?")[0]
        if path == "/health":
            mode = settings.health_mode
            status, body = (200 if mode == "ok" else 503), {"status": mode}
        elif path == "/version":
            status, body = 200, {"version": settings.version}
        else:
            status, body = 404, {"error": "not found"}

        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def create_server(settings, bind="0.0.0.0", *, port=None):
    address = (bind, settings.port if port is None else port)
    server = ThreadingHTTPServer(address, Handler)
    server.settings = settings
    return server


if __name__ == "__main__":
    try:
        settings = Settings.from_env()
    except ValueError as error:
        raise SystemExit(f"Invalid configuration: {error}")
    with create_server(settings) as server:
        print(f"Listening on {settings.port} · version {settings.version}", flush=True)
        server.serve_forever()
