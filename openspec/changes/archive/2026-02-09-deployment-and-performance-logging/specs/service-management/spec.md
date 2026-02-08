## ADDED Requirements

### Requirement: Cross-platform service management
The system SHALL provide a service management script that supports Mac, Linux, and Windows operating systems.

The script SHALL support the following operations:
- `install`: Register the application as a system service
- `uninstall`: Remove the system service registration
- `start`: Start the service (foreground or background)
- `stop`: Stop the running service
- `restart`: Restart the service
- `status`: Check if the service is running

#### Scenario: Install service on Linux
- **WHEN** user runs `sudo python scripts/service.py install` on Linux
- **THEN** system SHALL create a systemd service file at `/etc/systemd/system/stock-selector.service` and enable it for auto-start

#### Scenario: Install service on Mac
- **WHEN** user runs `sudo python scripts/service.py install` on macOS
- **THEN** system SHALL create a launchd plist file at `/Library/LaunchDaemons/com.stock-selector.plist` and load it

#### Scenario: Install service on Windows
- **WHEN** user runs `python scripts/service.py install` on Windows (as Administrator)
- **THEN** system SHALL register a Windows service using the Service Control Manager

#### Scenario: Start service in foreground
- **WHEN** user runs `python scripts/service.py start --foreground`
- **THEN** system SHALL start the application in the current terminal session with logs visible

#### Scenario: Start service in background
- **WHEN** user runs `python scripts/service.py start` (without --foreground)
- **THEN** system SHALL start the application as a background daemon/service

#### Scenario: Stop running service
- **WHEN** user runs `python scripts/service.py stop` and the service is running
- **THEN** system SHALL gracefully stop the service and log "Service stopped successfully"

#### Scenario: Check service status
- **WHEN** user runs `python scripts/service.py status`
- **THEN** system SHALL display whether the service is running, stopped, or not installed

### Requirement: Service auto-start on boot
When a service is installed, it SHALL be configured to automatically start on system boot.

#### Scenario: Service starts after reboot
- **WHEN** system reboots after service installation
- **THEN** the stock-selector service SHALL automatically start without manual intervention

#### Scenario: Service does not start after uninstall
- **WHEN** service is uninstalled and system reboots
- **THEN** the stock-selector service SHALL NOT start automatically

### Requirement: Service runs both API and scheduler
The installed service SHALL run both the FastAPI application and the APScheduler in a single process.

#### Scenario: Service starts API server
- **WHEN** service starts
- **THEN** the FastAPI application SHALL be accessible on the configured port (default 8000)

#### Scenario: Service starts scheduler
- **WHEN** service starts
- **THEN** the APScheduler SHALL be running and executing scheduled tasks according to cron configuration

#### Scenario: Service logs to file
- **WHEN** service is running in background mode
- **THEN** logs SHALL be written to a configured log file (e.g., `/var/log/stock-selector/app.log`)

### Requirement: Graceful shutdown
The service SHALL support graceful shutdown, allowing running tasks to complete before stopping.

#### Scenario: Graceful stop with running tasks
- **WHEN** user stops the service while a scheduled task is running
- **THEN** system SHALL wait for the task to complete (up to a timeout) before stopping

#### Scenario: Force stop after timeout
- **WHEN** graceful shutdown exceeds the configured timeout (default 30 seconds)
- **THEN** system SHALL force-stop the service and log a warning

### Requirement: Service configuration
The service SHALL read configuration from environment variables or a `.env` file.

#### Scenario: Load configuration from .env file
- **WHEN** service starts and a `.env` file exists in the application directory
- **THEN** system SHALL load all configuration variables from the `.env` file

#### Scenario: Environment variables override .env
- **WHEN** both `.env` file and system environment variables are present
- **THEN** system environment variables SHALL take precedence over `.env` file values
