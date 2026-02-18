## ADDED Requirements

### Requirement: Optimization page
The system SHALL provide a frontend page at route `/optimization` accessible from the sidebar navigation menu.

The page SHALL contain:
1. A task creation form with: strategy selector, parameter range inputs, stock code input, date range picker, algorithm selector (grid/genetic), initial capital input
2. A task list table showing: task_id, strategy_name, algorithm, status, progress bar, created_at, action buttons (view result)
3. A result detail view showing: best parameters table, top N results table with metrics, parameter heatmap chart (for 2-parameter strategies)

#### Scenario: Create optimization task from UI
- **WHEN** user fills the form and clicks "开始优化"
- **THEN** it SHALL call POST `/api/v1/optimization/run` and add the task to the list

#### Scenario: View optimization results
- **WHEN** user clicks "查看结果" on a completed task
- **THEN** it SHALL display the result detail view with best parameters and metrics table

### Requirement: Parameter range form
The parameter range form SHALL auto-populate with the strategy's default param_space when a strategy is selected.

Each parameter SHALL show: name, type, min, max, step inputs.

#### Scenario: Strategy selection populates param space
- **WHEN** user selects "ma-cross" strategy
- **THEN** the form SHALL show parameter inputs for fast (int, 3-20, step 1), slow (int, 10-60, step 5), vol_ratio (float, 1.0-3.0, step 0.1)

### Requirement: Navigation menu entry
The sidebar navigation SHALL include a "参数优化" menu item with an appropriate icon, positioned after "回测中心".

#### Scenario: Navigate to optimization page
- **WHEN** user clicks "参数优化" in the sidebar
- **THEN** the browser SHALL navigate to `/optimization`
