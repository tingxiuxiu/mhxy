# 文字西游 - 后端服务

文字型网络游戏后端，基于 FastAPI + PostgreSQL + Redis 实现。

## 技术栈

- **Web框架**: FastAPI
- **数据库**: PostgreSQL (asyncpg) + SQLAlchemy 2.0 (异步)
- **缓存/中间件**: Redis
- **配置管理**: pydantic-settings (.env)
- **包管理**: uv
- **测试**: pytest + pytest-asyncio + allure-pytest

## 快速开始

```bash
# 1. 安装依赖
uv sync --all-extras

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 修改数据库和Redis连接信息

# 3. 初始化数据库
uv run python init_db.py

# 4. 启动服务
uv run python run.py
# 或
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 生成Allure报告
uv run pytest tests/ --alluredir=allure-results
allure generate allure-results -o allure-report --clean
allure open allure-report
```

## API文档

启动服务后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
