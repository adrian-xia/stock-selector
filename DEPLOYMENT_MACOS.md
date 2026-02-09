# macOS 生产环境部署指南

## 1. 配置生产环境变量

编辑 `.env.prod` 文件，配置生产环境参数：

```bash
vim .env.prod
```

**必须配置的项：**
```bash
# 数据库（建议使用独立的生产数据库）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stock_selector_prod

# Gemini API（如果需要 AI 分析）
GEMINI_API_KEY=your-api-key-here

# Redis（可选）
REDIS_HOST=localhost
REDIS_PORT=6379

# 日志级别（生产环境建议用 INFO）
LOG_LEVEL=INFO
```

## 2. 创建生产数据库

```bash
# 创建独立的生产数据库
createdb stock_selector_prod

# 初始化数据库结构
export $(cat .env.prod | grep -v '^#' | xargs)
uv run alembic upgrade head
```

## 3. 初始化生产数据

```bash
# 运行数据初始化向导
export $(cat .env.prod | grep -v '^#' | xargs)
uv run python -m scripts.init_data

# 建议选择：最近 3 年数据（约 750 个交易日）
```

## 4. 安装并启动服务

```bash
# 安装服务（开机自启）
./scripts/service.sh install

# 或者只启动服务（不设置开机自启）
./scripts/service.sh start
```

## 5. 服务管理命令

```bash
# 启动服务
./scripts/service.sh start

# 停止服务
./scripts/service.sh stop

# 重启服务
./scripts/service.sh restart

# 查看状态
./scripts/service.sh status

# 查看实时日志
./scripts/service.sh logs

# 查看错误日志
./scripts/service.sh errors

# 卸载服务
./scripts/service.sh uninstall
```

## 6. 访问服务

服务启动后，访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/

## 7. 日志文件位置

- 标准输出：`~/Library/Logs/stock-selector.log`
- 错误输出：`~/Library/Logs/stock-selector.error.log`

## 8. 更新代码后的操作

```bash
# 1. 拉取最新代码
git pull

# 2. 更新依赖（如果有变化）
uv sync

# 3. 运行数据库迁移（如果有）
export $(cat .env.prod | grep -v '^#' | xargs)
uv run alembic upgrade head

# 4. 重启服务
./scripts/service.sh restart
```

## 9. 故障排查

### 服务无法启动

```bash
# 查看错误日志
./scripts/service.sh errors

# 或直接查看
tail -50 ~/Library/Logs/stock-selector.error.log
```

### 手动测试启动

```bash
# 使用启动脚本测试
./scripts/start_prod.sh

# 或手动加载环境变量启动
export $(cat .env.prod | grep -v '^#' | xargs)
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 检查 launchd 状态

```bash
# 查看服务是否加载
launchctl list | grep stock-selector

# 查看详细信息
launchctl print gui/$(id -u)/com.stock-selector
```

## 10. 开发和生产环境切换

### 开发环境（使用 .env）
```bash
uv run uvicorn app.main:app --reload
```

### 生产环境（使用 .env.prod）
```bash
./scripts/service.sh start
```

## 注意事项

1. **数据库隔离**：生产和开发使用不同的数据库，避免数据混淆
2. **日志级别**：生产环境使用 INFO，开发环境使用 DEBUG
3. **自动重启**：服务崩溃后会自动重启（KeepAlive 配置）
4. **开机自启**：使用 `install` 命令后，服务会在登录时自动启动
5. **端口占用**：确保 8000 端口未被其他程序占用
