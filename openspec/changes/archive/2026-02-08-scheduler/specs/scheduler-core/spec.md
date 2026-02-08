## ADDED Requirements

### Requirement: Scheduler creation and configuration
The system SHALL provide a `create_scheduler()` function that returns a configured `AsyncIOScheduler` instance with:
- MemoryJobStore (default)
- Timezone set to `Asia/Shanghai`
- `coalesce=True` to merge missed triggers
- `max_instances=1` per job
- `misfire_grace_time=300` (5 minutes)

#### Scenario: Scheduler created with correct timezone
- **WHEN** `create_scheduler()` is called
- **THEN** the returned scheduler SHALL have timezone set to `Asia/Shanghai`

#### Scenario: Missed triggers coalesced
- **WHEN** a job misses multiple trigger times (e.g., app was down)
- **THEN** the scheduler SHALL execute the job only once upon restart

### Requirement: Scheduler lifecycle management
The system SHALL provide `start_scheduler()` and `stop_scheduler()` functions for integration with FastAPI lifespan.

`start_scheduler()` SHALL:
- Create the scheduler instance
- Register all cron jobs
- Start the scheduler

`stop_scheduler()` SHALL:
- Gracefully shut down the scheduler (wait for running jobs to complete)

#### Scenario: Scheduler starts with FastAPI
- **WHEN** the FastAPI application starts (lifespan startup)
- **THEN** the scheduler SHALL be started and all jobs SHALL be registered

#### Scenario: Scheduler stops gracefully
- **WHEN** the FastAPI application shuts down (lifespan shutdown)
- **THEN** the scheduler SHALL wait for any running job to complete before stopping

### Requirement: Job registration
The system SHALL provide a `register_jobs(scheduler)` function that registers all cron jobs to the scheduler.

Each job SHALL be registered with:
- A unique `job_id` string
- A cron trigger with the configured schedule
- `replace_existing=True` to allow re-registration on restart

#### Scenario: All jobs registered on startup
- **WHEN** `register_jobs()` is called
- **THEN** the post-market chain job and weekend stock sync job SHALL be registered

#### Scenario: Jobs survive restart
- **WHEN** the application restarts and `register_jobs()` is called again
- **THEN** existing jobs SHALL be replaced without duplication
