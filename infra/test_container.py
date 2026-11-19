def test_application_files(host):
    for path in ("/srv/app/app.py", "/srv/app/settings.py"):
        assert host.file(path).is_file


def test_running_application_process(host):
    command = host.file("/proc/1/cmdline").content
    assert command.split(b"\0")[0].endswith(b"python")
    assert b"app.py" in command


def test_tcp_listener(host):
    check = (
        "import os, socket; "
        "socket.create_connection(('127.0.0.1', int(os.environ['APP_PORT'])), timeout=2).close()"
    )
    assert host.run("python -c %s", check).rc == 0


def test_application_process_uid(host):
    status = host.file("/proc/1/status").content_string
    uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
    user_ids = [int(field) for field in uid_line.split()[1:]]
    assert user_ids == [10001] * 4
