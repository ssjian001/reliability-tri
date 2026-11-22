# CHANGELOG — 三件套 V1.1 · Engineering Implementation Ready

升级日期：2026-11-22。两轮修订：第一轮（快改）落地评审意见初稿；本轮（实施就绪版）按 Implementation Readiness Review 结论定案，并产出可直接交给开发团队的机读附件。

## 1. 评审意见逐项处理

| 编号 | 评审问题 | 处理级别 | V1.1 处理结果 |
|---|---|---|---|
| 01 | Expression 求值语义 | 核心技术决策，必须明确 | **已完成**：01 §3.1 规则引擎架构定案（Parser/AST→Unit Norm→Evaluator）；02 §2.1 DSL 白名单（比较/逻辑/算术/受限 IF，禁函数调用）、单位归一先于求值、错误码（MISSING_INPUT/DIV_BY_ZERO/DIMENSION_MISMATCH）；rule.schema.json 含 expression 约束 |
| 02 | A 级证据冲突裁决 | 必须建立优先级与阻断机制 | **已完成**：02 §3.1 裁决矩阵（手册=极限值、标准=降额系数、企业规范=应用边界）、硬约束（不得放宽绝对最大额定值/强制要求）、`CONFLICT_UNRESOLVED` 阻断自动放行转人工 |
| 03 | 基准集标注 Schema | 决定指标是否可信 | **已完成**：附件 benchmark.schema.json + 03 §4.1（expected_findings/not_expected/rationale/adjudication；双标一致性 ≥80%；仅 agreed/resolved 参与计分） |
| 04 | 评分者一致性 | 必须加入评审校准机制 | **已完成**：03 §7（试评 10 条对齐；一致率 <80% 暂停重训；Cohen's/加权 Kappa、Fleiss'/Krippendorff's Alpha；原始分保留；分歧进仲裁集） |
| 05 | 分析规模与性能边界 | 必须量化系统负载 | **已完成**：01 §5A 容量表定案（BOM 500 行/3 工况/1500 组合/5 并发/50MB/2GB；P95≤30s 口径=单分析 Run 的规则分析任务，不含外部仿真求解、长文件解析、人工审批；BOM 硬上限 2000 行） |
| 06 | DFMEA 评分模板 | 补充可配置默认模板 | **已完成**：附件 dfmea_scoring_template.md（S/O/D 三档判据 + AIAG-VDA AP 网格；建议起点，企业批准后替换；S=H 保底进高风险清单） |
| 07 | 标准版权合规 | 建立标准元数据管理 | **已完成**：02 §3.2 + 01 §9A（只存元数据+条款号+受控副本指针；全文不入库不展示；部署侧治理随立项确定） |
| 08 | 首批规则与知识规模 | 明确 MVP 交付数量 | **已完成**：02 §4.1（规则每族 ≥10 条、合计 ≥60 条、失效模式 ≤200 条精选）+ 01 §11（计划表退出条件补齐） |
| 09 | 分级回归机制 | 降低模型迭代成本 | **已完成**：03 §11 分级回归表（5 类变更 × 5 档范围）+ 全量盲测成本口径 |
| 10 | Prompt Injection 语料库 | 建立安全测试集 | **已完成**：附件 prompt_injection_dataset.json（22 条，6 类载荷形态：bom_comment/datasheet_cell/pdf_hidden_text/report_field/knowledge_entry/markdown_link） |
| 11 | ReliaTrack 集成 | 建立试验数据闭环 | **已完成**：01 §11A 定案批量交换（实查无 REST API）；附件 reliatrack-interface-spec.md（字段映射/交换机制/幂等/校验/升级触发条件）；03 §3 集成测试挂契约测试 |
| 12 | 视觉/文档其余建议（P95 口径引用、评分表引用、计划表退出条件） | 文档完善 | **已完成**：01 §8/§11、02 §2、03 §2 等散点修订 |

## 2. 新增三项（本轮方案提出）

| 项 | 处理结果 |
|---|---|
| A. 分析结果确定性与可复现性 | **已完成**：01 §3.2（同输入+同版本 ⇒ 确定性结果逐字节一致；LLM 差异不得改变确定性结果；AnalysisRun 记录五类版本）；03 §2 增可复现性验证原则 |
| B. 规则覆盖率管理 | **已完成**：01 §4A 四项指标（器件类别覆盖比/失效机理覆盖比/未覆盖高风险场景数/适用性不确定比例）进报告中心与发布评审；02 §9 纳入监控；FR12 立项 |
| C. ReliaTrack 可靠性闭环 | **已完成**：01 §11A 四步数据链（识别→承接→回灌→专家审核更新）；interface-spec §1 数据链表 + §3.2 FA 输入映射；知识更新不自动修改正式规则 |

## 3. 交付物清单

| 交付物 | 文件 | 状态 |
|---|---|---|
| 01 系统工程规格书 V1.1-ER | 01_系统工程规格书.md | 已完成 |
| 02 规则与知识库规范 V1.1-ER | 02_可靠性规则与知识库规范.md | 已完成 |
| 03 验证与验收规范 V1.1-ER | 03_验证与验收规范.md | 已完成 |
| Rule Schema | attachments/rule.schema.json | 已完成 |
| Benchmark Schema | attachments/benchmark.schema.json | 已完成 |
| Unit Dictionary | attachments/unit_dictionary.yaml | 已完成（温度仿射、别名、错误规则） |
| DFMEA Scoring Template | attachments/dfmea_scoring_template.md | 已完成（待企业批准） |
| Prompt Injection Dataset | attachments/prompt_injection_dataset.json | 已完成（22 条 ≥20） |
| ReliaTrack Interface Spec | attachments/reliatrack-interface-spec.md | 已完成（定案批量交换） |
| Change Log | CHANGELOG.md | 本文件 |

## 4. 遗留与说明

- 02 §7.1 / 附件评分表为**建议起点**，发布前须企业批准口径（标记保留）。
- ReliaTrack 接口为 CSV/Excel 批量交换；实时 API 的升级触发条件写在 interface-spec §6。
- 原评审意见全文与 V1.0 原件 zip 另存（不在本目录）。
- 单位字典的温度仿射换算（degC↔K↔degF）为声明式描述，引擎实现时按 Pint 的 affine 转换落地。

## 5. V1.1-ER-r2（2026-11-22）：协同评审合并轮

来源：协作者对 V1.1-ER 第一轮的补充（核心数据模型修订版、分层规则 YAML 模板、REST API 修订清单、Datasheet 管线、03 三补丁）+ 本方技术把关（两类执行器边界、schema 同步）。全部并入。

| 项 | 处理结果 | 落点 |
|---|---|---|
| 修订版核心数据模型（MeasuredParam/ComponentStress/Artifact/SimulationJob/Finding 标签化） | **已完成**：01 §5 全面替换（§5.0-5.4 分层）；net_name 预留 EDA 网表；conclusion_tag 四分类从 Schema 层强制防幻觉；data_gaps 落 Finding | 01 §5 |
| 分层规则 YAML 模板（declarative_expr/lookup_curve/script_plugin） | **已完成**：02 §2.2 三类定义 + 附件 rule_templates.yaml（三条完整规则）+ rule.schema.json 扩 rule_type/curve_eval/plugin_ref/oneOf 条件必填/tests 容差 | 02 §2.2、01 §3.1 |
| 修订版 REST API 清单（四资源分组、202+run_id、rules 生命周期 :test/:promote/:rollback、artifacts 上传、stresses 批量、findings 分页、reports:export） | **已完成**：01 §6 全量替换（§6.1-6.4） | 01 §6 |
| Datasheet 抽取与人机协同管线（五步 + D 级防呆） | **已完成**：01 §7A 新增；未人工确认的抽取参数强制 confidence_level=D，禁用于正式判定 | 01 §7A |
| 03 补丁①：高风险统一定量口径 | **已完成**：03 §2.1 三条件任一 + 0% 漏报红线与双人签核挂钩 | 03 §2.1 |
| 03 补丁②：数值容差与边界 | **已完成**：03 §5.1（逻辑判定 100% 一致 + 相对误差 ≤0.1% 或绝对误差工程最小有效位；超差 S1） | 03 §5.1 |
| 03 补丁③：评分仲裁机制 | **已完成**：03 §7（≥2 分分歧/关键事实错误/漏报相左 → 第三人仲裁，沉淀新基准样本走 §4.1 schema） | 03 §7 |
| 落地衔接（asteval/simpleeval、插值引擎、白名单插件包、容差挂钩） | **已完成**：01 §3.1 三执行器定案 + 02 §2.2 类型约束 + rule.schema.json oneOf | 01/02/schema |
| 新增附件 rule_templates.yaml | 三条完整示例规则（RES-PWR/MOS-SOA/ECAP-LIFE），含 SKIPPED_PRECONDITION、expected_outputs、tolerance_rel 示范 | attachments/ |

## 6. 本轮技术把关记录（两处边界消解）

1. lookup_curve/script_plugin 与 01 §3.1「禁函数调用」的表面冲突：禁令收窄为仅约束 declarative_expr 的 expression；三类 rule_type 各走专属执行器（DSL 求值器 / 曲线插值引擎 / 受控白名单插件），插件注册表版本化+审计，已在 01 §3.1 与 02 §2.2 双向写死。
2. rule.schema.json 与 02 正文的机读/人读分工：不一致时以 JSON Schema 为准（02 §2 已声明）。
