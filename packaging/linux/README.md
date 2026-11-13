# Local Ubuntu desktop launcher

Install one **ECHO** app entry. Launching it opens the full interactive
workbench on `127.0.0.1:8766`, with case navigation, provider actions, and
investigation drafts enabled. Provider requests happen only when explicitly
started in the interface.

The app entry also has an **Open read-only walkthrough** action. That opens the
retained Rio Grande do Sul T163 case on `127.0.0.1:8765` in server-enforced,
single-case read-only mode. It blocks provider requests and investigation
draft changes. These are two access modes of one application, not separate
products; each runs as its own local systemd service so the read-only boundary
is enforced by the server.

The app menu includes separate Restart and Stop actions for both modes. Normal
launch reuses an active service; Restart reloads backend code from the current
checkout and interrupts active requests in that mode. Both services bind to
loopback and open the browser; neither exposes ECHO to another machine.

From the repository root, install the launcher in the current user's app menu:

```bash
chmod +x packaging/linux/echo-desktop-launcher.sh
install -Dm644 packaging/linux/echo.desktop \
  "$HOME/.local/share/applications/echo.desktop"
rm -f "$HOME/.local/share/applications/echo-investigation.desktop" \
  "$HOME/.local/share/applications/echo-workbench.desktop"
```

Launch **ECHO** from the Ubuntu app grid. The main entry opens
`http://127.0.0.1:8766/`; choose **Open read-only walkthrough** in the app
actions for `http://127.0.0.1:8765/`. Use the matching Restart or Stop action
for the selected mode. Logs can be inspected with:

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
