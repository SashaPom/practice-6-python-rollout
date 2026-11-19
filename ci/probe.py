import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def probe(origin, path, expected):
    try:
        with urlopen(origin + path, timeout=3) as response:
            code, body = response.status, response.read().decode("utf-8")
    except HTTPError as error:
        with error:
            print(f"HTTP {error.code} {path} {error.read().decode('utf-8')}")
        return False
    except (URLError, TimeoutError) as error:
        print(f"Request failed for {path}: {error}")
        return False

    print(f"HTTP {code} {path} {body}")
    try:
        return code == 200 and json.loads(body) == expected
    except json.JSONDecodeError:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("version")
    args = parser.parse_args()
    origin = args.origin.rstrip("/")
    health_ok = probe(origin, "/health", {"status": "ok"})
    version_ok = probe(origin, "/version", {"version": args.version})
    raise SystemExit(0 if health_ok and version_ok else 1)
