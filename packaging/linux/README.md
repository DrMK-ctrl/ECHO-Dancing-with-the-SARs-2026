# Local Ubuntu desktop launcher

Two user-level launchers are available:

- **ECHO SAR Investigation** opens the retained Rio Grande do Sul T163 case in
  server-enforced, single-case read-only mode on `127.0.0.1:8765`.
- **ECHO Interactive Workbench** starts the normal local application on
  `127.0.0.1:8766`, with case navigation, provider actions, and investigation
  drafts enabled. Provider requests occur only when explicitly initiated in the
  interface; no request is made merely by launching the app.

Each mode runs as a separate user systemd service and has its own Stop action.
Both bind to loopback and open the browser; neither exposes the app to another
machine.

From the repository root, install the launcher in the current user's app menu:

```bash
chmod +x packaging/linux/echo-desktop-launcher.sh
install -Dm644 packaging/linux/echo-investigation.desktop \
  "$HOME/.local/share/applications/echo-investigation.desktop"
install -Dm644 packaging/linux/echo-workbench.desktop \
  "$HOME/.local/share/applications/echo-workbench.desktop"
```

Launch either app from the Ubuntu app grid. Their addresses are
`http://127.0.0.1:8765/` and `http://127.0.0.1:8766/`. Use each app's Stop
action to stop its service. Logs can be inspected with:

```bash
journalctl --user -u echo-local-demo.service
journalctl --user -u echo-local-workbench.service
```

Prerequisites are the repository's installed `.venv`, a running user systemd
manager, `curl`, `xdg-open`, and a browser. The desktop file points to this
checkout's absolute path; moving the checkout requires updating its `Exec` and
`Icon` paths and reinstalling the desktop entry. Optional NASA GIBS map tiles
still require internet access. This is a local launcher, not a packaged or
portable application build.
