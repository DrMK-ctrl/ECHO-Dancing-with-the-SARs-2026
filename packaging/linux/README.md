# Local Ubuntu desktop launcher

This launcher opens the retained Rio Grande do Sul T163 investigation in ECHO's
server-enforced, single-case read-only mode. It binds only to `127.0.0.1:8765`,
starts the server as a user systemd service, and opens the browser. It does not
start a provider search or use Earthdata credentials.

From the repository root, install the launcher in the current user's app menu:

```bash
chmod +x packaging/linux/echo-desktop-launcher.sh
install -Dm644 packaging/linux/echo-investigation.desktop \
  "$HOME/.local/share/applications/echo-investigation.desktop"
```

Launch **ECHO SAR Investigation** from the Ubuntu app grid. To stop the local
server, use the app's **Stop ECHO local server** action. The app server is
available at `http://127.0.0.1:8765/` while it is running. Its user-service log
can be inspected with:

```bash
journalctl --user -u echo-local-demo.service
```

Prerequisites are the repository's installed `.venv`, a running user systemd
manager, `curl`, `xdg-open`, and a browser. The desktop file points to this
checkout's absolute path; moving the checkout requires updating its `Exec` and
`Icon` paths and reinstalling the desktop entry. Optional NASA GIBS map tiles
still require internet access. This is a local launcher, not a packaged or
portable application build.
