## ADDED Requirements

### Requirement: Package application for deployment
The system SHALL provide a packaging script that creates a deployable tarball containing all necessary files for production deployment.

The package SHALL include:
- All source code from the `app/` directory
- Dependency lock file (`uv.lock`)
- Configuration template (`.env.example`)
- Documentation (`README.md`)
- Exclusion of development files (tests, `.git`, `__pycache__`, etc.)

#### Scenario: Successful packaging
- **WHEN** user runs `python scripts/package.py`
- **THEN** the system SHALL create a tarball at `dist/stock-selector-<version>.tar.gz` containing all required files

#### Scenario: Version from git tag
- **WHEN** the repository has a git tag (e.g., `v1.0.0`)
- **THEN** the package filename SHALL use the tag version (e.g., `stock-selector-v1.0.0.tar.gz`)

#### Scenario: Version from commit hash
- **WHEN** the repository has no git tags
- **THEN** the package filename SHALL use the short commit hash (e.g., `stock-selector-a1b2c3d.tar.gz`)

### Requirement: Validate package contents
The packaging script SHALL validate that all required files are present before creating the tarball.

Required files:
- `app/main.py` (application entry point)
- `uv.lock` (dependency lock file)
- `.env.example` (configuration template)
- `README.md` (documentation)

#### Scenario: Missing required file
- **WHEN** a required file is missing (e.g., `uv.lock` not found)
- **THEN** the packaging script SHALL fail with an error message indicating which file is missing

#### Scenario: All files present
- **WHEN** all required files are present
- **THEN** the packaging script SHALL proceed with tarball creation

### Requirement: Log packaging progress
The packaging script SHALL log progress information during the packaging process.

#### Scenario: Progress logging
- **WHEN** the packaging script runs
- **THEN** it SHALL log: version detection, file collection count, validation status, and final tarball path

#### Scenario: Packaging completion
- **WHEN** packaging completes successfully
- **THEN** the script SHALL log "打包完成：dist/stock-selector-<version>.tar.gz (X.X MB)"
