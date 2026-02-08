## ADDED Requirements

### Requirement: Package application for deployment
The system SHALL provide a packaging script that creates a deployable application package containing all necessary components for production deployment.

The package SHALL include:
- Python application code and dependencies
- Configuration file templates (.env.example)
- Startup scripts for the application and scheduler
- Database migration scripts (Alembic)
- Documentation (README, deployment guide)

#### Scenario: Create deployment package
- **WHEN** user runs `uv run python scripts/package.py`
- **THEN** system SHALL create a `dist/stock-selector-<version>.tar.gz` file containing all application files and dependencies

#### Scenario: Package includes dependencies
- **WHEN** packaging script runs
- **THEN** the package SHALL include a `requirements.txt` or `uv.lock` file with all Python dependencies pinned to specific versions

#### Scenario: Package includes configuration templates
- **WHEN** packaging script runs
- **THEN** the package SHALL include `.env.example` with all required configuration variables documented

#### Scenario: Package includes startup scripts
- **WHEN** packaging script runs
- **THEN** the package SHALL include executable scripts for starting the API server and scheduler

#### Scenario: Package is portable
- **WHEN** package is extracted on a target system with Python 3.12+
- **THEN** the application SHALL be runnable after installing dependencies and configuring environment variables

### Requirement: Support version tagging
The packaging script SHALL automatically include version information in the package name and metadata.

#### Scenario: Version from git tag
- **WHEN** packaging script runs in a git repository with tags
- **THEN** it SHALL use the latest git tag as the version number (e.g., `v1.0.0`)

#### Scenario: Version from commit hash
- **WHEN** packaging script runs without git tags
- **THEN** it SHALL use the short commit hash as the version identifier (e.g., `abc1234`)

### Requirement: Validate package contents
The packaging script SHALL validate that all required files are present before creating the package.

#### Scenario: Missing critical files
- **WHEN** packaging script runs and critical files are missing (e.g., `app/main.py`)
- **THEN** it SHALL fail with a clear error message listing the missing files

#### Scenario: Successful validation
- **WHEN** all required files are present
- **THEN** packaging script SHALL proceed to create the package and log "Package validation successful"
