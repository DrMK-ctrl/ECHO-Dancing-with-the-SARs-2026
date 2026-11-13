from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "packaging/linux/echo-desktop-launcher.sh"


def _fake_command(directory: Path, name: str, body: str) -> None:
    executable = directory / name
    executable.write_text(f"#!/bin/sh\nset -eu\n{body}\n", encoding="utf-8")
    executable.chmod(0o755)


def _launcher_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "services"
    bin_dir.mkdir()
    state_dir.mkdir()
    _fake_command(
        bin_dir,
        "systemctl",
        'case "$2" in\n'
        '  is-active) test -f "$FAKE_STATE_DIR/$4" ;;\n'
        '  stop) printf "%s\\n" "$3" >> "$FAKE_STOP_LOG"; rm -f "$FAKE_STATE_DIR/$3" ;;\n'
        '  *) exit 90 ;;\n'
        'esac',
    )
    _fake_command(
        bin_dir,
        "systemd-run",
        'for arg do case "$arg" in --unit=*) unit="${arg#--unit=}" ;; esac; done\n'
        'test -n "${unit:-}"\n'
        'printf "%s\\n" "$@" >> "$FAKE_RUN_LOG"\n'
        'touch "$FAKE_STATE_DIR/$unit.service"',
    )
    _fake_command(
        bin_dir,
        "curl",
        'printf "%s\\n" "$*" >> "$FAKE_CURL_LOG"\n'
        'test -n "$(find "$FAKE_STATE_DIR" -type f -print -quit)" || exit 1\n'
        'if [ -n "${FAKE_CURL_BODY:-}" ]; then printf "%s" "$FAKE_CURL_BODY"; '
        'elif printf "%s" "$*" | grep -q 8766; then '
        'printf \'{"record_type":"ECHO_LOCAL_CASE_REGISTRY","access_mode":"INTERACTIVE_LOCAL","cases":[{}]}\'; '
        'else printf \'{"record_type":"ECHO_LOCAL_CASE_REGISTRY","access_mode":"CURATED_READ_ONLY","cases":[{}]}\'; fi',
    )
    _fake_command(bin_dir, "xdg-open", 'printf "%s\\n" "$1" >> "$FAKE_OPEN_LOG"')
    _fake_command(bin_dir, "sleep", ":")
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "FAKE_STATE_DIR": str(state_dir),
            "FAKE_RUN_LOG": str(tmp_path / "systemd-run.log"),
            "FAKE_CURL_LOG": str(tmp_path / "curl.log"),
            "FAKE_OPEN_LOG": str(tmp_path / "open.log"),
            "FAKE_STOP_LOG": str(tmp_path / "stop.log"),
        }
    )
    return env


def _run_launcher(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LAUNCHER), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_demo_launcher_is_loopback_only_and_starts_curated_read_only_case(tmp_path: Path):
    env = _launcher_env(tmp_path)

    result = _run_launcher(env, "--demo")

    assert result.returncode == 0, result.stderr
    run_args = Path(env["FAKE_RUN_LOG"]).read_text(encoding="utf-8")
    assert "--host\n127.0.0.1\n" in run_args
    assert "--port\n8765\n" in run_args
    assert "--read-only-demo" in run_args
    assert "data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json" in run_args
    assert Path(env["FAKE_OPEN_LOG"]).read_text(encoding="utf-8").strip() == "http://127.0.0.1:8765/"


def test_default_launcher_opens_interactive_workbench_on_loopback(tmp_path: Path):
    env = _launcher_env(tmp_path)

    result = _run_launcher(env)

    assert result.returncode == 0, result.stderr
    run_args = Path(env["FAKE_RUN_LOG"]).read_text(encoding="utf-8")
    assert "--unit=echo-local-workbench" in run_args
    assert "--host\n127.0.0.1\n" in run_args
    assert "--port\n8766\n" in run_args
    assert "--read-only-demo" not in run_args
    assert Path(env["FAKE_OPEN_LOG"]).read_text(encoding="utf-8").strip() == "http://127.0.0.1:8766/"


def test_desktop_menu_has_one_main_echo_entry_with_read_only_action():
    desktop_entries = sorted((ROOT / "packaging/linux").glob("*.desktop"))

    assert [entry.name for entry in desktop_entries] == ["echo.desktop"]
    content = desktop_entries[0].read_text(encoding="utf-8")
    assert "Name=ECHO\n" in content
    assert "Actions=ReadOnlyDemo;" in content


@pytest.mark.parametrize(
    ("launch_args", "service", "url"),
    [
        ((), "echo-local-workbench.service", "http://127.0.0.1:8766/"),
        (("--demo",), "echo-local-demo.service", "http://127.0.0.1:8765/"),
    ],
)
def test_normal_launch_reuses_active_service_without_restarting_it(
    tmp_path: Path, launch_args: tuple[str, ...], service: str, url: str
):
    env = _launcher_env(tmp_path)
    (Path(env["FAKE_STATE_DIR"]) / service).touch()

    result = _run_launcher(env, *launch_args)

    assert result.returncode == 0, result.stderr
    assert not Path(env["FAKE_RUN_LOG"]).exists()
    assert not Path(env["FAKE_STOP_LOG"]).exists()
    assert Path(env["FAKE_OPEN_LOG"]).read_text(encoding="utf-8").strip() == url


@pytest.mark.parametrize(
    ("restart_flag", "service", "unit", "port", "access_mode"),
    [
        ("--restart", "echo-local-workbench.service", "echo-local-workbench", "8766", "INTERACTIVE_LOCAL"),
        ("--restart-demo", "echo-local-demo.service", "echo-local-demo", "8765", "CURATED_READ_ONLY"),
    ],
)
def test_explicit_restart_replaces_only_its_mode_and_opens_current_service(
    tmp_path: Path, restart_flag: str, service: str, unit: str, port: str, access_mode: str
):
    env = _launcher_env(tmp_path)
    state_dir = Path(env["FAKE_STATE_DIR"])
    (state_dir / service).touch()
    (state_dir / "other-mode.service").touch()
    env["FAKE_CURL_BODY"] = (
        '{"record_type":"ECHO_LOCAL_CASE_REGISTRY",'
        f'"access_mode":"{access_mode}","cases":[{{}}]}}'
    )

    result = _run_launcher(env, restart_flag)

    assert result.returncode == 0, result.stderr
    run_args = Path(env["FAKE_RUN_LOG"]).read_text(encoding="utf-8")
    assert f"--unit={unit}" in run_args
    assert f"--port\n{port}\n" in run_args
    assert Path(env["FAKE_STOP_LOG"]).read_text(encoding="utf-8").strip() == service
    assert (state_dir / service).exists()
    assert (state_dir / "other-mode.service").exists()
    assert Path(env["FAKE_OPEN_LOG"]).read_text(encoding="utf-8").strip().endswith(f":{port}/")


def test_launcher_does_not_open_an_unrelated_service_on_its_port(tmp_path: Path):
    env = _launcher_env(tmp_path)
    env["FAKE_CURL_BODY"] = "<html>unrelated local service</html>"

    result = _run_launcher(env)

    assert result.returncode == 1
    assert not Path(env["FAKE_OPEN_LOG"]).exists()
    assert Path(env["FAKE_RUN_LOG"]).exists()


@pytest.mark.parametrize(
    ("stop_flag", "stopped_unit", "still_active_unit"),
    [
        ("--stop", "echo-local-workbench.service", "echo-local-demo.service"),
        ("--stop-demo", "echo-local-demo.service", "echo-local-workbench.service"),
    ],
)
def test_stopping_one_launcher_mode_leaves_the_other_service_running(
    tmp_path: Path, stop_flag: str, stopped_unit: str, still_active_unit: str
):
    env = _launcher_env(tmp_path)
    state_dir = Path(env["FAKE_STATE_DIR"])
    (state_dir / "echo-local-demo.service").touch()
    (state_dir / "echo-local-workbench.service").touch()

    result = _run_launcher(env, stop_flag)

    assert result.returncode == 0, result.stderr
    assert not (state_dir / stopped_unit).exists()
    assert (state_dir / still_active_unit).exists()
