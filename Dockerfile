# ============================================
# Stage 1: 前端构建
# ============================================
FROM node:22-alpine AS frontend-build

WORKDIR /build/web

# 先复制依赖清单，利用 Docker 缓存
COPY web/package.json web/pnpm-lock.yaml ./
RUN corepack enable && corepack prepare pnpm@latest --activate && pnpm install --frozen-lockfile

# 复制前端源码并构建
COPY web/ ./
RUN pnpm build

# ============================================
# Stage 2: 运行时（Python + nginx + supervisor）
# ============================================
FROM python:3.13-slim

# 设置时区为 Asia/Shanghai
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor tzdata && \
    rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先复制依赖清单，利用 Docker 缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# 复制后端源码
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY scripts/ ./scripts/

# 从 Stage 1 复制前端构建产物
COPY --from=frontend-build /build/web/dist ./web/dist/

# 配置文件
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 暴露端口：5173（nginx 前端）、8000（uvicorn 后端）
EXPOSE 5173 8000

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
