#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="demo"
if [[ "${1:-}" == "--interactive" || "${1:-}" == "--stop-interactive" ]]; then
    mode="interactive"
fi

if [[ "$mode" == "interactive" ]]; then
    mode_label="interactive workbench"
    service_name="echo-local-workbench.service"
    url="http://127.0.0.1:8766/"
    port="8766"
    case_file="data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json"
else
    mode_label="read-only investigation"
    service_name="echo-local-demo.service"
    url="http://127.0.0.1:8765/"
    port="8765"
    case_file="data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json"
fi

if [[ "${1:-}" == "--stop" || "${1:-}" == "--stop-interactive" ]]; then
    if systemctl --user is-active --quiet "$service_name"; then
        systemctl --user stop "$service_name"
        notify-send "ECHO stopped" "The local $mode_label server has stopped." 2>/dev/null || true
    else
        notify-send "ECHO is not running" "There is no local ECHO demo server to stop." 2>/dev/null || true
    fi
    exit 0
fi

if ! systemctl --user is-active --quiet "$service_name"; then
    extra_args=()
    if [[ "$mode" == "demo" ]]; then
        extra_args+=(--read-only-demo)
    fi
    systemd-run --user --unit="${service_name%.service}" --collect --quiet \
        --property="WorkingDirectory=$project_root" \
        --property=Restart=on-failure \
        "$project_root/.venv/bin/echo" serve \
        --host 127.0.0.1 \
        --port "$port" \
        --case-file "$case_file" \
        "${extra_args[@]}"
fi

for _ in {1..40}; do
    if curl --fail --silent --output /dev/null "$url"; then
        xdg-open "$url"
        exit 0
    fi
    if ! systemctl --user is-active --quiet "$service_name"; then
        break
    fi
    sleep 0.25
done

notify-send "ECHO did not start" \
    "Check the user journal with: journalctl --user -u $service_name" \
    2>/dev/null || true
exit 1
