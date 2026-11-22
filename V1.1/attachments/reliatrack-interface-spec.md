# ReliaTrack 接口规范（CSV/Excel 批量交换适配器）V1.0

> 前置结论（2026-11-22 代码实查）：ReliaTrack 为 PySide6 桌面应用（MVC + apsw/SQLite，schema v29/20 表），**无任何 Web/REST 框架**——V1.1 采用 CSV/Excel 批量交换适配器；实时 API 集成留待 ReliaTrack 侧演进后升级（触发条件：ReliaTrack 引入 HTTP 服务层）。
> 代码事实依据：`reliatrack/src/services/export_service.py`、`export_handlers.py`（csv/xlsx 导出面）；表清单来自 `src/db/schema.py`（CREATE TABLE 实取）。

## 1. 数据链（对应 01 §11A 闭环）

| 方向 | 数据 | 源/目标表（ReliaTrack） | 本系统落点 |
|---|---|---|---|
| ← 导入 | 试验计划（目的/条件/样品量/判据） | test_plans、test_tasks | VerificationTest、DVP&R 对照（FR08） |
| ← 导入 | 试验结果 | test_results、samples、sample_transactions | Evidence（B 级，附 checksum） |
| ← 导入 | 失效记录 | fa_records、issues | FA 输入（FR07）、失效模式库案例 |
| ← 导入 | CAPA | capa_records | FR10 风险闭环的验证证据 |
| → 导出 | 验证计划 | —（人工承接为 test_plans） | DVP&R 导出（FR08） |
| → 导出 | 风险清单 | —（人工承接为 issues） | Finding 导出（FR10） |

## 2. 交换机制（V1.1 定案）

- **载体**：CSV（UTF-8，逗号分隔，RFC 4180）为主；Excel 为人工审阅辅载体。
- **目录约定**：ReliaTrack 导出落 `exports/`（现状目录）；本系统适配器监控固定交换目录 `exchange/outbound|inbound`（部署时映射）。
- **触发**：手动导入为主（试点期）；文件到达自动解析为 P1 增强。不引入常驻服务。
- **幂等**：每批文件头携带 `batch_id`（导出时间戳+行数）；本系统按 batch_id + 行校验值去重。
- **频率**：试点期按需手动；常态建议每项目每里程碑一批。

## 3. 字段映射

### 3.1 试验结果 → Evidence（B 级）
| ReliaTrack 列（test_results/samples） | 本系统字段 | 约束 |
|---|---|---|
| 记录 id / 任务 id | evidence_id 后缀 | 必填，保序 |
| test_results.result | 结论 | pass/fail 枚举映射 |
| test_results.measured_value | 实测值+单位 | 单位经 unit_dictionary 归一 |
| test_plans.condition | 测试条件 | 必填 |
| samples.sample_size | 样本量 | 必填 |
| 文件/图片引用 | source_uri+checksum | 必填 |
| 导出时间与版本 | revision/version_date | 必填 |

### 3.2 失效记录 → FA 输入（FR07）
| ReliaTrack 列（fa_records/issues） | 本系统字段 |
|---|---|
| 现象描述 | FA 现象输入 |
| 发生条件/工况 | OperatingProfile 对齐字段 |
| 样品信息（refdes/料号） | BomItem/Component 关联 |
| 根因/结论 | 候选机理候选池（标注为 C 级证据，除非有 B 级实测支撑） |
| CAPA（capa_records） | FR10 措施与验证证据 |

### 3.3 验证计划 → ReliaTrack（出向）
| 本系统字段（FR08 DVP&R） | ReliaTrack 承接列（人工建 test_plans） |
|---|---|
| 目的/方法 | test_plans 计划描述 |
| 条件/判据 | test_tasks 判据字段 |
| 样品量 | samples 初始化 |
| FA 要求 | issues 预建关联 |

出向为**人工承接**（试点期不自动写 ReliaTrack），导出为受控 Excel 模板，列名与 ReliaTrack 现有列对齐，避免批量写入破坏其状态机。

## 4. 校验与异常处理

- 导入前置校验：字段齐全、单位可归一（unit_dictionary）、日期格式、枚举合法；非法行整行拒收并输出错误清单（行号+原因），**不部分入库**。
- 版本冲突：同 batch_id 重复导入 → 按幂等跳过；同引用不同内容 → 冲突清单转人工。
- 单位异常：UNKNOWN_UNIT/DIMENSION_MISMATCH 报错不入库（与 02 §2.1 一致）。
- 断链保护：适配器只读写交换目录，不直接连 ReliaTrack 的 SQLite（避免锁/写冲突）。
- 审计：每批导入/导出记 batch_id、操作人、行数、拒收数到审计日志（01 §9）。

## 5. 验收（挂 03 §3 集成层）

- 契约测试：样例导出文件（ReliaTrack 真实导出脱敏）→ 导入 → Evidence/FA 字段逐项比对。
- 异常用例：坏编码、缺列、单位未知、batch_id 重复、checksum 不符——全部拒收且给出行级原因。
- 回归：ReliaTrack schema 升版（v29→v30+）时映射表复核为发布门禁项。

## 6. 升级触发条件

ReliaTrack 侧出现以下任一情况时，评估升级为实时 API 集成：引入 HTTP 服务层；提供机器可读的事件推送；多系统消费需求成立。届时本文件改为 API 契约（OpenAPI），批量适配器保留为降级路径。
