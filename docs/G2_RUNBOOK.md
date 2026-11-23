# G2 本地运行手册

## 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[test]"
```

## 配置与迁移

```bash
export RELIABILITY_DATABASE_URL="sqlite:///./reliability_tri.db"
# 本地可不设置 API key；非本地环境必须设置：
export RELIABILITY_API_KEY="replace-with-a-long-random-secret"
PYTHONPATH=src alembic upgrade head
```

## 启动

```bash
PYTHONPATH=src uvicorn reliability_api.main:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/docs` 查看 Swagger UI；`/openapi.json` 为 OpenAPI 3.1 契约。设置 API key 后，在 Swagger Authorize 中输入 Bearer token。

## 测试

```bash
PYTHONPATH=src pytest -q tests/g1 tests/g2
python tools/validate_assets.py
```

## 安全提醒

- 不设置 `RELIABILITY_API_KEY` 仅限本地开发，不能绑定公网地址。
- `X-Actor-ID` 是审计字段，不代表可信认证身份。
- 当前 API 的同步分析适合功能验证，不适合长时间、大批量任务。
- `script_plugin` 的 OS 沙箱生产门禁仍遵循 G1 验收报告，不因 API 包装而解除。
