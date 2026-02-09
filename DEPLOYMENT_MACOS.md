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
# 启动服务（同时启动前端 + 后端）
./scripts/service.sh start

# 停止服务（同时停止前端 + 后端）
./scripts/service.sh stop

# 重启服务
./scripts/service.sh restart

# 查看状态（显示前端和后端各自的运行状态及最近日志）
./scripts/service.sh status

# 查看后端实时日志
./scripts/service.sh logs

# 查看后端错误日志
./scripts/service.sh errors

# 查看前端实时日志
tail -f ~/Library/Logs/stock-selector-frontend.log

# 卸载服务
./scripts/service.sh uninstall
```

## 6. 访问服务

服务启动后，访问：
- **前端界面**：http://localhost:5173
- **后端 API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/

服务会同时启动前端（React + Vite）和后端（FastAPI），无需分别启动。

## 7. 日志文件位置

- **后端标准输出**：`~/Library/Logs/stock-selector.log`
- **后端错误输出**：`~/Library/Logs/stock-selector.error.log`
- **前端输出**：`~/Library/Logs/stock-selector-frontend.log`

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
# 查看后端错误日志
./scripts/service.sh errors

# 或直接查看
tail -50 ~/Library/Logs/stock-selector.error.log

# 查看前端日志
tail -50 ~/Library/Logs/stock-selector-frontend.log
```

### 手动测试启动

```bash
# 使用启动脚本测试（会同时启动前端和后端）
./scripts/start_prod.sh

# 或手动加载环境变量启动后端
export $(cat .env.prod | grep -v '^#' | xargs)
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# 手动启动前端（在另一个终端）
cd web
pnpm dev
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
# 后端
uv run uvicorn app.main:app --reload

# 前端（在另一个终端）
cd web
pnpm dev
```

### 生产环境（使用 .env.prod）
```bash
# 前端和后端一起启动
./scripts/service.sh start
```

## 注意事项

1. **数据库隔离**：生产和开发使用不同的数据库，避免数据混淆
2. **日志级别**：生产环境使用 INFO，开发环境使用 DEBUG
3. **自动重启**：后端崩溃后会自动重启（KeepAlive 配置），前端随后端一起由 `start_prod.sh` 拉起
4. **开机自启**：使用 `install` 命令后，服务会在登录时自动启动
5. **端口占用**：确保 8000（后端）和 5173（前端）端口未被其他程序占用
6. **前端进程管理**：前端以后台进程运行，PID 记录在 `/tmp/stock-selector-frontend.pid`，停止服务时会自动清理
