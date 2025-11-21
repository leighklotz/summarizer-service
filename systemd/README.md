# Systemd Integration for Summarizer Service

This directory contains a systemd user service for managing the Summarizer Service as a supervised background process. It replaces the older `crontab @reboot` + `screen` method and provides:

- Automatic start on login (or full boot if lingering is enabled)
- Automatic restart on failure
- Clean logs via `journalctl`
- No need for `screen` or manual restarts

## Files

### `summarizer-service.service`
A systemd user unit that launches the service by running `../run.sh` in the repository root. This allows systemd to directly supervise the gunicorn process.

### `install.sh`
A helper script that installs the user unit, reloads systemd, enables the service, and starts it immediately.

## Installation

Run the installer from the repository root:

```bash
cd /home/klotz/wip/summarizer-service/systemd
./install.sh
```

This script will:

1. Create `~/.config/systemd/user/` if necessary  
2. Copy `summarizer-service.service` into it  
3. Reload the systemd user daemon  
4. Enable the service for auto-start  
5. Start the service immediately  

Verify that the service is running:

```bash
systemctl -l --user status summarizer-service.service
```

View logs:

```bash
journalctl -l --user -u summarizer-service.service -e
```

## Managing the Service: start, stop, and restart

```bash
systemctl --user start summarizer-service.service
systemctl --user stop summarizer-service.service
systemctl --user restart summarizer-service.service
```

## Uninstall

Disable and remove the service:

```bash
systemctl --user disable --now summarizer-service.service
rm ~/.config/systemd/user/summarizer-service.service
systemctl --user daemon-reload
```

## Service Behavior

The service:

- Runs `run.sh` from the repository root
- Uses the project’s Python virtual environment (`.venv/bin`)
- Restarts automatically on failure
- Logs output to the systemd journal

## Example Directory Layout

```
summarizer-service/
  run.sh
  startservice.sh
  summarizer_service/
  systemd/
    README.md
    summarizer-service.service
    install.sh
```
