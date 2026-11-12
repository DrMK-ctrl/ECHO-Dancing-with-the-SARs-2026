# Ubuntu desktop launcher check

**Date:** 2026-11-12

**Result:** Both local service lifecycles passed; GNOME app-grid activation remains unverified.

## Implemented

- Added a user-level desktop entry using the EESAR Systems logo.
- Launcher starts the existing T163 investigation on `127.0.0.1:8765` in the server-enforced `--read-only-demo` mode and opens the local browser.
- Desktop action stops the user systemd service. It does not invoke a provider or require Earthdata credentials.
- Installed the desktop entry in `~/.local/share/applications/echo-investigation.desktop` on the development laptop.

## Checks

- `bash -n packaging/linux/echo-desktop-launcher.sh`: passed.
- `desktop-file-validate` on the source and installed desktop entries: passed.
- Running the launcher script started `echo-local-demo.service`; `ss` showed the server listening only on `127.0.0.1:8765`.
- Browser navigation opened the existing local browser session.
- HTTP 200: `/`, `/api/cases`, `/api/case`, `/api/review`, `/api/cross-sensor-assessment`, `/api/adversarial-challenge` for the retained water hypothesis, and `/api/dswx-context`.
- HTTP 403: `POST /api/catalog` in curated read-only mode.
- The desktop Stop action made the service inactive and the local URL unreachable (curl status `000`).
- `gtk-launch echo-investigation` could not run: the host helper aborts because the installed GNOME settings schema lacks `org.gnome.settings-daemon.plugins.xsettings/antialiasing`. Therefore activation through the GNOME app grid itself is not verified, despite the valid installed desktop file.

## Interactive workbench check

- Added and installed **ECHO Interactive Workbench** as a second user-level desktop entry. It starts normal app mode on `127.0.0.1:8766`, using a separate `echo-local-workbench.service`; it does not use `--read-only-demo`.
- Running the launcher opened the local browser and started the service. The listener was `127.0.0.1:8766`.
- `GET /api/cases` returned HTTP 200 with six registered cases and `provider_actions_enabled=true`. `GET /api/investigation-drafts` returned HTTP 200 with zero drafts.
- No provider endpoint was requested and no draft was created.
- The Interactive Workbench Stop action made the service inactive and the local URL unreachable (curl status `000`).
- `bash -n` and `desktop-file-validate` passed for the launcher and both desktop entries.
- `tests/test_linux_desktop_launcher.py`: **4 passed**. The regression checks assert both mode-specific ports and flags, loopback binding, and independent stop behavior.
- Full repository suite after adding these checks: `.venv/bin/python -m pytest -q` — **491 passed**.

Both modes were also run simultaneously. At `127.0.0.1:8765`, the demo returned `CURATED_READ_ONLY`, one case, and provider actions disabled. At `127.0.0.1:8766`, the workbench returned `INTERACTIVE_LOCAL`, six cases, and provider actions enabled. Stopping the demo left the workbench active and reachable; stopping the workbench then closed its port. Neither listener bound to a non-loopback address.

This is a checkout-bound local launcher, not a portable package. Moving the repository requires updating its absolute `Exec` and `Icon` paths. Optional NASA GIBS map imagery still needs internet access. No external access or deployment is configured.

## Startup identity guard recheck — 2026-11-12

The launcher previously treated any successful HTTP response at its local URL as
ready. It now requests `/api/cases` and checks the ECHO registry record type, a
nonempty case list, and the expected mode (`CURATED_READ_ONLY` or
`INTERACTIVE_LOCAL`) before opening the browser. This prevents a different local
service occupying the configured port from being mistaken for ECHO.

- `bash -n` and `desktop-file-validate`: passed.
- `gio launch` of the installed `echo-investigation.desktop`: returned successfully;
  the existing service remained active from the authoritative checkout and served
  the expected one-case `CURATED_READ_ONLY` registry.
- A launcher regression test supplied unrelated HTML on the port and confirmed
  that no browser was opened; both launcher modes and independent stop behavior
  also passed. Focused suite: **5 passed**.
- Full suite: `.venv/bin/python -m pytest -q` — **498 passed**.

The GNOME Shell app-grid activation itself remains unverified. The earlier
`gtk-launch` attempt failed in the host GTK helper because its expected
GSettings `antialiasing` key is absent; that is an environment limitation, while
the installed desktop file was activated successfully through GIO. The launcher
uses the current checkout and `.venv`; Python source updates require a service
restart to load, after which the same desktop entry uses the updated code.
