## ADDED Requirements

### Requirement: Detect operating system platform
The service management script SHALL detect the current operating system platform and select the appropriate service manager.

Supported platforms:
- Linux: use systemd
- macOS: use launchd
- Windows: not supported in V1 (future enhancement)

#### Scenario: Linux platform detection
- **WHEN** the script runs on a Linux system
- **THEN** it SHALL use systemd for service management

#### Scenario: macOS platform detection
- **WHEN** the script runs on a macOS system
- **THEN** it SHALL use launchd for service management

#### Scenario: Unsupported platform
- **WHEN** the script runs on Windows or an unsupported platform
- **THEN** it SHALL exit with an error message "不支持的操作系统：<platform>"

### Requirement: Install service
The service management script SHALL support installing the application as a system service with auto-start on boot.

For Linux (systemd):
- Create service file at `/etc/systemd/system/stock-selector.service`
- Enable the service with `systemctl enable stock-selector`

For macOS (launchd):
- Create plist file at `~/Library/LaunchAgents/com.stock-selector.plist`
- Load the service with `launchctl load`

#### Scenario: Install service on Linux
- **WHEN** user runs `python scripts/service.py install` on Linux
- **THEN** the system SHALL create a systemd service file and enable auto-start

#### Scenario: Install service on macOS
- **WHEN** user runs `python scripts/service.py install` on macOS
- **THEN** the system SHALL create a launchd plist file and load the service

#### Scenario: Service already installed
- **WHEN** the service is already installed
- **THEN** the script SHALL prompt the user to uninstall first or use `--force` to overwrite

### Requirement: Start and stop service
The service management script SHALL support starting and stopping the service.

#### Scenario: Start service on Linux
- **WHEN** user runs `python scripts/service.py start` on Linux
- **THEN** the system SHALL execute `systemctl start stock-selector`

#### Scenario: Stop service on Linux
- **WHEN** user runs `python scripts/service.py stop` on Linux
- **THEN** the system SHALL execute `systemctl stop stock-selector`

#### Scenario: Start service on macOS
- **WHEN** user runs `python scripts/service.py start` on macOS
- **THEN** the system SHALL execute `launchctl start com.stock-selector`

#### Scenario: Stop service on macOS
- **WHEN** user runs `python scripts/service.py stop` on macOS
- **THEN** the system SHALL execute `launchctl stop com.stock-selector`

### Requirement: Check service status
The service management script SHALL support checking the current status of the service.

#### Scenario: Check status on Linux
- **WHEN** user runs `python scripts/service.py status` on Linux
- **THEN** the system SHALL execute `systemctl status stock-selector` and display the output

#### Scenario: Check status on macOS
- **WHEN** user runs `python scripts/service.py status` on macOS
- **THEN** the system SHALL execute `launchctl list | grep stock-selector` and display the output

### Requirement: Uninstall service
The service management script SHALL support uninstalling the service and removing all service files.

#### Scenario: Uninstall service on Linux
- **WHEN** user runs `python scripts/service.py uninstall` on Linux
- **THEN** the system SHALL stop the service, disable auto-start, and remove the service file

#### Scenario: Uninstall service on macOS
- **WHEN** user runs `python scripts/service.py uninstall` on macOS
- **THEN** the system SHALL unload the service and remove the plist file

### Requirement: Support foreground mode
The service management script SHALL support running the application in foreground mode for debugging.

#### Scenario: Foreground mode
- **WHEN** user runs `python scripts/service.py start --foreground`
- **THEN** the system SHALL start the application directly without using the service manager and log to stdout

### Requirement: Graceful shutdown
The application SHALL support graceful shutdown, waiting for running tasks to complete before stopping.

#### Scenario: Graceful shutdown with timeout
- **WHEN** the service receives a stop signal
- **THEN** it SHALL wait up to 30 seconds for running tasks to complete before forcing shutdown

#### Scenario: No running tasks
- **WHEN** the service receives a stop signal and no tasks are running
- **THEN** it SHALL stop immediately
