# Ubuntu desktop launcher check

**Date:** 2026-11-12

**Result:** Local service lifecycle and read-only app routes passed; GNOME app-grid activation remains unverified.

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

This is a checkout-bound local launcher, not a portable package. Moving the repository requires updating its absolute `Exec` and `Icon` paths. Optional NASA GIBS map imagery still needs internet access. No external access or deployment is configured.
