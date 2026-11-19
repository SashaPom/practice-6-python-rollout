import json
from contextlib import contextmanager
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from app import create_server
from settings import Settings


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("APP_PORT", "8080")
    monkeypatch.setenv("APP_VERSION", "unit-42")
    monkeypatch.setenv("APP_HEALTH_MODE", "ok")

    @contextmanager
    def running():
        with create_server(Settings.from_env(), "127.0.0.1", port=0) as server:
            worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
            worker.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}"
            finally:
                server.shutdown()
                worker.join(timeout=2)

    return running


def get_json(origin, path):
    try:
        response = urlopen(origin + path, timeout=2)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


@pytest.mark.parametrize(
    "path, code, body",
    [
        ("/health", 200, {"status": "ok"}),
        ("/version", 200, {"version": "unit-42"}),
        ("/unknown", 404, {"error": "not found"}),
    ],
)
def test_routes(api, path, code, body):
    with api() as origin:
        assert get_json(origin, path) == (code, body)


def test_unhealthy_mode_returns_503(api, monkeypatch):
    monkeypatch.setenv("APP_HEALTH_MODE", "down")
    with api() as origin:
        assert get_json(origin, "/health") == (503, {"status": "down"})


@pytest.mark.parametrize(
    "name, value",
    [
        ("APP_PORT", "abc"),
        ("APP_PORT", "0"),
        ("APP_PORT", "65536"),
        ("APP_VERSION", " "),
        ("APP_HEALTH_MODE", "unknown"),
    ],
)
def test_invalid_environment_is_rejected(monkeypatch, name, value):
    monkeypatch.setenv("APP_PORT", "8080")
    monkeypatch.setenv("APP_VERSION", "unit-42")
    monkeypatch.setenv("APP_HEALTH_MODE", "ok")
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        Settings.from_env()


def test_version_comes_from_environment(api, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "preview-7")
    with api() as origin:
        assert get_json(origin, "/version") == (200, {"version": "preview-7"})
