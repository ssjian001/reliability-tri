# AI电子硬件可靠性分析系统｜三件套交付包
版本 V1.1-ER-r3｜2026-11-22（V1.0｜2026-11-21）

## 文件清单
1. `01_系统工程规格书.md`：架构、功能需求、统一结构化数据模型（MeasuredParam/ComponentStress）、异步 API 契约、Datasheet 解析管线与实施计划。
2. `02_可靠性规则与知识库规范.md`：分层规则 Schema（表达式/曲线查表/计算插件）、证据等级、失效模式库、DFMEA 及知识维护。
3. `03_验证与验收规范.md`：基准集、高风险量化口径、测试矩阵、AI 评估指标、浮点容差、发布门禁和试点验收。
4. `CHANGELOG.md`：V1.0→V1.1 全部修订的逐项追溯。
5. `attachments/`：机读交付物（rule.schema.json、benchmark.schema.json、unit_dictionary.yaml、dfmea_scoring_template.md、prompt_injection_dataset.json、rule_templates.yaml、reliatrack-interface-spec.md）。

## 版本变更摘要（V1.0 → V1.1）
- **模型对齐与应力解耦**：统一物理量值对象 MeasuredParam，新增器件实际工作应力 ComponentStress、多模态附件 Artifact 及 SimulationJob 实体，消除文档间字段断层。
- **规则引擎表达力扩展**：规则细分为 declarative_expr、lookup_curve 与 script_plugin 三类，覆盖 SOA 包络与寿命曲线计算。
- **数据入库与 API 完备化**：明确 Datasheet 人机校对入库流水线，补全规则生命周期管理、异步任务查询及报告导出接口。
- **验收口径量化**：明确「高风险」定量边界、数值容差 |Δ| ≤ max(abs_floor, rel×ref)（Arrhenius 寿命类 rel=0.01）及专家盲测仲裁机制。

## 使用建议
- 01用于立项、架构评审及研发任务拆解。
- 02用于规则引擎和可靠性知识库建设。
- 03用于测试团队、领域专家和业务Owner验收。
文中阈值、样本量和KPI均为建议基线，需结合产品、适用标准、企业规范及风险等级批准，不自动构成强制标准。

## V1.1 修订说明（2026-11-22）
评审后修订：01 增规模与性能边界、既有系统接口、首批规模基线与基准集生产工作量；02 增表达式与单位规范、A 级冲突裁决、标准版权合规、首批规模基线、默认评分表模板；03 增基准集样本 Schema、场景覆盖矩阵、注入语料基线、分级回归与评分者一致性校验。各文档末尾附修订记录。

## 正式开发前需补齐
目标产品线、企业标准清单、试点项目 BOM 与工况采集模板、PLM/EDA/实验室接口、部署环境、数据分级策略和责任矩阵。
