# G2 API 与数据契约阶段验收报告

- 版本：G2 MVP 0.2.0
- 日期：2026-11-23
- 基线：V1.1.1 + G1 Engine MVP 0.1.0
- 结论：**功能级验收通过；生产部署验收不通过（有明确未关闭项）**

## 1. 交付范围

| 工作包 | 交付 | 状态 |
|---|---|---|
| REST API | FastAPI 路由、请求/响应模型、OpenAPI 3.1 | PASS |
| Rule 数据契约 | JSON Schema 校验、Rule 主记录、不可变 RuleVersion、内容哈希、版本唯一约束 | PASS |
| Analysis 数据契约 | AnalysisRun、Finding、规则版本快照和结果持久化 | PASS |
| Curve Artifact | 曲线网格、单位、插值方法、来源引用、checksum、审批门禁 | PASS |
| Approval / Audit | 审批记录、审计事件、创建者不得自批的流程检查 | PASS（非强身份保证） |
| 幂等 | 分析请求 Idempotency-Key，同 key 同 payload 重放、异 payload 冲突 | PASS |
| 数据库迁移 | Alembic initial migration，SQLite migration 与 metadata drift check | PASS |
| API 安全 | 可选 Bearer API Key | CONDITIONAL |

## 2. 接口范围

- `POST /v1/rules`：创建 draft 规则。
- `GET /v1/rules`、`GET /v1/rules/{rule_id}`：查询规则及版本。
- `POST /v1/rules/{rule_id}/versions`：创建新版本，不覆盖旧版本。
- `POST /v1/rules/{rule_id}:test`：调用 G1 执行规则。
- `POST /v1/rules/{rule_id}:validate`：运行内置测试集；全部匹配预期状态后才能发布。
- `POST /v1/curves`：创建待审批曲线工件。
- `GET /v1/curves/{curve_id}`：查询曲线工件。
- `POST /v1/approvals`：审批发布规则或批准曲线。
- `POST /v1/analyses/derating`：同步执行已发布的 derating/power/thermal 规则。
- `GET /v1/analyses/{run_id}`、`GET /v1/analyses/{run_id}/findings`：查询分析与 Finding。
- `GET /v1/audit-events`：查询审计事件。
- `GET /health`、`GET /openapi.json`：健康检查和 API 契约。

## 3. 自动化验证

- G1 + G2 自动化测试：**40 / 40 PASS**。
- Alembic：全新 SQLite 数据库 `upgrade head` PASS。
- Alembic drift check：`No new upgrade operations detected`。
- Python compileall：PASS。
- V1.1.1 资产校验：3 条规则模板 PASS；benchmark sample PASS；Prompt Injection 数据集 22 项；单位精确别名冲突 0；总体 PASS。

## 4. 生产化未关闭项

1. **身份与权限：** 当前单一共享 API Key，不是用户身份系统；`X-Actor-ID` 是调用方声明字段，不能作为审批身份依据。上线前接入 OIDC/OAuth2、用户/角色 RBAC、服务身份和可信审计主体。
2. **多租户隔离：** 尚无 tenant_id、行级隔离、项目 ACL；多客户数据不能共库直接开放。
3. **任务执行：** 分析目前同步执行，缺少 worker queue、超时取消、重试、任务租约和崩溃恢复。
4. **审批状态机：** 当前实现最小发布门禁；需补齐 reviewer 权限、双人/多级审批、拒绝原因、撤销发布、废弃和回滚策略。
5. **数据库：** SQLite 用于开发验证；生产需 PostgreSQL、连接池、备份恢复演练、TLS、迁移回滚策略。
6. **曲线来源：** checksum 仅证明输入载荷未被意外改变，不证明 datasheet 真实性、坐标数字化准确性或专家审核质量。
7. **幂等保留：** 当前无自动 TTL 清理，生产需保留期限和唯一键冲突恢复策略。
8. **接口运营：** 尚未实现速率限制、请求体大小限制、游标分页、API deprecation policy、全面指标和 tracing。

## 5. 退出判断

G2 已打通 G1 到 REST API 和数据库持久化的最小闭环，可进入 G3 规则库建设与 G4 Benchmark 数据建设并行阶段。但在真实用户/客户数据、生产审批或公网部署前，必须关闭上述安全与运维门禁；尤其不得把 `X-Actor-ID` 字段检查误认为真实双人审批。
