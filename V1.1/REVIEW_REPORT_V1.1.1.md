# reliability-tri V1.1 技术评审报告（V1.1.1 Review Patch）

- 评审对象：用户上传的 `reliability-tri-main.zip`
- 评审范围：`V1.1/` 内 3 份规范、CHANGELOG、README、JSON Schema、YAML 规则模板、单位字典、DFMEA 模板、Prompt Injection 数据集、ReliaTrack 接口规范
- 评审日期：2026-11-22
- 评审方式：静态文档审查 + JSON Schema Draft 2020-12 校验 + YAML/JSON 解析 + 机读附件交叉检查
- 未评审范围：后端源码、数据库迁移、API 实现、CI/CD、部署配置、运行时安全、真实 ReliaTrack 源码与接口（本次 ZIP 未包含这些内容）

## 1. 总体结论

**有条件通过（Conditional Pass）**

V1.1 的系统方向正确：规则优先、确定性计算与 LLM 分离、结论标签化、输入快照和版本留痕、人工审批、高风险漏报优先等原则具备工程价值。核心文档覆盖了智能硬件可靠性分析系统的主要模块。

但原始 V1.1 **不能按文档自述直接认定为 Engineering Implementation Ready**。原始规则模板与机读 Schema 存在系统性不一致，单位系统有可能造成前缀和温度量纲错误，Benchmark Schema 无法保存双人独立标注，ReliaTrack 的关键架构结论缺少本次交付包内的可核验证据。此外，API 契约、运行时实现和端到端验收材料仍未交付。

本补丁已修复可在文档/附件层解决的问题；未能从现有资料证实的内容均保留为 TBD，不以推测填补。

## 2. 评审维度

| 维度 | 结论 | 说明 |
|---|---|---|
| 系统架构与职责边界 | 通过 | 规则引擎、RAG、LLM、审批和证据层的分工合理 |
| 规则 Schema 与模板一致性 | 原版不通过；补丁后通过静态校验 | 三条模板原版全部违反 Schema；补丁后均通过 |
| 单位体系与 DSL 安全边界 | 有条件通过 | 已修正主要单位歧义；仍需真实解析器、量纲测试和温度仿射测试 |
| 证据治理与标准版权 | 有条件通过 | 原则正确；需补充标准版本适用性与冲突仲裁实例 |
| Benchmark 与 AI 评估 | 原版不通过；补丁后结构改善 | 增加双人独立原始标注；尚无真实标注集和一致性统计 |
| DFMEA 评分 | 有条件通过 | 27 组合已补齐，但仍是内部示例映射，不是官方 AIAG-VDA AP 表 |
| ReliaTrack 集成 | 待现场核实 | 当前 ZIP 无 ReliaTrack 源码/API 文档，无法验证是否存在 REST API |
| API、性能与部署 | 有条件通过 | 有资源清单和性能目标，缺 OpenAPI、实测环境和压测报告 |
| 安全与提示注入 | 有条件通过 | 22 条载荷语料已具备；没有执行框架/红队结果，不能据此判定安全通过 |
| 工程实施就绪度 | 不通过（尚未达到） | 当前交付是设计规范与附件，不是可运行系统或可验收构建产物 |

## 3. 原始版本关键问题与补丁处理

### P1 — Rule Schema 与 YAML 规则模板契约不一致

**原始证据：**
- Schema 全局要求 `expression`，但 `lookup_curve`、`script_plugin` 规则按正文设计不使用顶层 expression。
- Schema 要求 `preconditions` 为字符串，模板提供 YAML 数组。
- Schema 的 threshold 对象要求 `value/unit/source_ref`，模板使用 `default/high_reliability/source`。
- Schema 的 evidence 要求 `level/publisher/title/version_date/locator`，模板只给 `evidence_id/page_or_section`。
- 模板状态使用 `approved`，Schema 只允许 `draft/in_review/tested/shadow/published/deprecated`。
- Schema 要求每条规则至少 3 个 tests，原模板分别只有 2、1、1 个。
- Schema 要求 test `expected`，模板使用 `expected_pass` 或 `expected_status`。

**补丁处理：**修订 `rule.schema.json` 和 `rule_templates.yaml`；规则示例状态统一为 `draft`；明确占位证据不得作为真实证据发布；增加插件参数来源/审批字段。

**复测：**3 条规则模板均通过 Draft 2020-12 JSON Schema 校验。

### P1 — 单位字典存在前缀/量纲语义风险

**原始风险：**
- 全局别名大小写不敏感会使 SI 前缀区分丢失，例如 mW/MW、mA/MA、mOhm/MOhm。
- 摄氏温度别名 `C` 与电荷量单位 C 有冲突风险。
- 温度绝对值与温差的转换语义未分离。
- 模板存在温度常量比较，若一律归一到 K 而表达式仍使用裸常量 70，会产生量纲或数值错误。

**补丁处理：**
- SI 符号按大小写敏感处理；自然语言别名仅在无歧义时允许大小写归一。
- 绝对温度仿射归一到 K；温差使用独立 `temperature_difference` 量纲。
- DSL 有量纲常量必须显式带单位后缀，如 `70[degC]`；AST 保留 Quantity/量纲，不剥离为裸浮点数。
- 增加 dimensionless/ratio、thermal_resistance、cycle_count 和非物理 `table` 类型。
- 单位字典精确别名扫描未发现重复冲突。

**仍需验证：**温度仿射转换、温差运算、量纲乘除、前缀大小写、未知单位、曲线轴单位及跨量纲拒绝的真实自动化测试。

### P1 — Benchmark Schema 不能证明双人独立标注

**原始问题：**原 Schema 仅记录两位 reviewer 的名字，没有保存两位评审者分别认为哪些风险应出现/不应出现，无法复算标注一致率或 Kappa。

**补丁处理：**增加 `annotations[]`，分别保存两位标注者的 expected_findings、not_expected、rationale；仲裁后的 canonical 答案与原始标注分开保存。新增示例样本并通过 Schema 校验。

**仍需验证：**应用层必须校验 reviewer 与 annotations 一一对应、两位 annotator_id 不重复、resolved 必须有完整仲裁记录；JSON Schema 本身无法完整实现这些跨字段业务约束。

### P1 — ReliaTrack “代码实查无 REST API”不可由本次上传内容支持

**原始问题：**接口规范声称已检查 PySide6/SQLite、schema v29/20 表且无 REST API，但本次 ZIP 仅包含 reliability-tri 文档，没有 ReliaTrack 源码、提交哈希、数据库 Schema 或接口文档。

**补丁处理：**删除确定性断言，改为“现状待核实”；CSV/Excel 作为暂定低耦合路径，REST API 作为现场核查后的候选优先路径。不得将未核实的技术栈写成事实。

**关闭条件：**提供 ReliaTrack 源码快照/commit、数据库 Schema 或维护者确认的 API 文档，并记录核查日期和版本。

### P2 — DFMEA AP 网格存在未定义组合

**原始问题：**原模板只列部分组合，“其余组合按 S/O 降序”不具备唯一性，且忽略 D 维度；同时“AIAG-VDA AP 风格”容易被误解为官方评分表。

**补丁处理：**补齐 27 种 H/M/L 组合，写明内部映射规则；明确它不是 AIAG-VDA 官方 AP 表。增加无数据时输出 TBD、S=H 始终进入高风险清单的约束。

**关闭条件：**由企业 DFMEA Owner 批准，按企业历史案例校准发生度区间和 AP 行动要求。

### P2 — 性能 P95 目标缺少可复现测量基线

当前 500 BOM × 3 工况、1500 组合、5 并发、P95≤30s 是合理的容量目标，但没有规定 CPU/RAM/存储/数据库、数据集规模、缓存冷热状态、测量次数、预热、统计窗口和压测工具。当前只能视为目标值，不是已验证性能。

### P1 — API 仍是端点清单，不是可交付 API 契约

当前列出了 REST 资源和路径，但没有 OpenAPI 3.x 文件、请求/响应 JSON Schema、认证与授权细则、幂等键算法、错误码目录、分页游标、限流策略、任务重试/取消、版本兼容策略。研发团队仍需补充契约后才能并行开发。

### P1 — 数据模型的“Schema 层强制”尚无实现证据

`MeasuredParam`、`Finding.conclusion_tag` 等目前是文档中的伪代码/逻辑数据模型。没有数据库 DDL、ORM Model、API JSON Schema 或迁移脚本，因而“从数据库 Schema 层强制”目前属于设计要求，不是已实现事实。

### P2 — 规则首批规模目标与实际交付物不同

规范提出首批规则 ≥60 条、关键规则族每族 ≥10 条，但附件仅提供 3 条示例模板。它们适合验证结构，不等于已交付 60 条经证据审查、测试和批准的正式规则。需把“模板数”和“正式规则数”分开统计。

### P2 — Prompt Injection 语料不等于安全验收通过

附件包含 22 条载荷，覆盖 BOM、Datasheet、PDF 隐藏文本、报告字段、知识库和 Markdown 链接。当前是测试数据，不是已执行的红队测试。需定义每条样本的攻击目标、测试入口、断言、预期拒绝行为和执行日志，并纳入 CI。

## 4. 本轮自动校验结果

| 检查项 | 结果 |
|---|---|
| Rule JSON Schema Draft 2020-12 自身合法性 | PASS |
| Benchmark JSON Schema Draft 2020-12 自身合法性 | PASS |
| 3 条 Rule YAML 模板对 Rule Schema 校验 | 3/3 PASS |
| Benchmark 示例对 Benchmark Schema 校验 | PASS |
| Prompt Injection 语料条数 | 22（满足 ≥20） |
| Unit Dictionary YAML 解析 | PASS |
| Unit Dictionary 完全相同别名冲突 | 0 |
| 规则模板是否代表真实批准规则 | NO，均为 draft 示例 |
| 后端/API/数据库/CI 是否已运行验证 | 未提供，未验证 |

以上是静态资产校验，不代表计算引擎的表达式执行正确，也不代表插件隔离、权限或提示注入防护已通过运行时测试。

## 5. 实施就绪前必须关闭的门禁

| 门禁 | 交付证据 | 状态 |
|---|---|---|
| G1 规则引擎 | DSL Parser/AST、单位量纲测试、曲线插值测试、插件沙箱测试 | 未关闭 |
| G2 数据契约 | OpenAPI 3.x、Rule/Benchmark/MeasuredParam/Finding Schema、数据库迁移 | 未关闭 |
| G3 规则库 | ≥60 条规则逐条证据审查、单测、Owner/Reviewer 签核 | 未关闭 |
| G4 基准集 | 双人独立标注、仲裁记录、一致性统计、盲测冻结 | 未关闭 |
| G5 性能 | 固定硬件/软件环境、压测脚本、P95/P99 报告、5 并发验证 | 未关闭 |
| G6 安全 | 22 条注入用例执行结果、越权/数据隔离/文件解析红队报告 | 未关闭 |
| G7 ReliaTrack | 源码/API 现状核查记录、脱敏样例文件、导入导出契约测试 | 未关闭 |
| G8 部署与运维 | 部署拓扑、密钥/备份/恢复、审计保留、监控告警和回滚演练 | 未关闭 |

## 6. 最终评审意见

**规格与机读附件层面：有条件通过。** 本轮已修复能够基于上传内容直接确认的结构性问题。

**工程实施就绪层面：暂不通过。** 主要原因不是总体架构方向错误，而是 API/数据契约、运行时实现、规则库规模、基准集实标、性能和安全验证尚无交付证据。

建议下一阶段不要继续堆叠长篇设计文档，而是以 G1–G8 为开发门禁，优先实现最小闭环：BOM/应力导入 → 单位/参数校验 → 3 类规则执行器 → Finding/Evidence → 人工处置 → 可复现报告 → CI 回归。
