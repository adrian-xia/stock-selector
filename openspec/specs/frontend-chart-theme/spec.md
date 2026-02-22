## ADDED Requirements

### Requirement: ECharts 公共主题配置
系统 SHALL 提供统一的 ECharts 主题配置文件，定义颜色方案、tooltip 样式、grid 布局等公共配置。

#### Scenario: 所有图表使用统一主题
- **WHEN** 任何 ECharts 图表组件渲染
- **THEN** SHALL 使用公共主题中定义的颜色方案和样式
- **AND** tooltip、legend、grid 等公共配置 SHALL 保持一致

#### Scenario: 股票涨跌颜色规范
- **WHEN** 图表需要表示涨跌
- **THEN** 涨 SHALL 使用红色（#ef4444），跌 SHALL 使用绿色（#22c55e）
- **AND** 该颜色规范 SHALL 在 K 线图、收益曲线等所有相关图表中统一

### Requirement: 图表配置工具函数
系统 SHALL 提供工具函数，用于合并公共主题和组件特定配置。

#### Scenario: 组件自定义配置覆盖公共配置
- **WHEN** 组件传入自定义 ECharts option
- **THEN** 工具函数 SHALL 将自定义配置与公共主题深度合并
- **AND** 组件特定配置 SHALL 优先于公共主题配置
