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

## 7. V1.1-ER-r3（2026-11-22）：复审修复轮

来源：协作者对 fcec5ac 的机读级复审（jsonschema 实测 39 errors + 逐节评审，全文存档 docs/review/irr-review-v1.0.md）。**39 errors 复现确认（15/12/12 分布一致）**，逐项修复如下。

### P0（阻断项，全部清零）
| 项 | 修复结果 |
|---|---|
| P0-1 模板与 Schema 矛盾（39 errors） | **0 errors 实测通过**（jsonschema Draft202012）。schema 侧：expression 移出顶层 required（allOf 按 rule_type 条件必填）、tests.required 收窄为 name+inputs、preconditions 数组化 [{expr,on_fail}]、thresholds 支持 variants、error_code/expected_status 增 CONFLICT_UNRESOLVED、inputs.source 受控枚举+quantity_kind+type；模板侧：日期加引号、status=published、evidence 补全、tests 补齐 ≥3 且 kind 覆盖、thresholds 改 variants |
| P0-2 温度归一矛盾 | **已完成**：unit_dictionary 温度双轨（temperature_abs→K 带偏移 / temperature_delta→K 差值）；inputs/outputs/插件参数全部带 quantity_kind；模板 2 折减因子改 delta 语义（25→1.00、85→0.52、150→0.00 手算复核） |
| P0-3 前置条件无机器语义 | **已完成**：preconditions 数组化 [{expr, on_fail}]（expr 只读 inputs，白名单同 expression）；01 §7.1 状态机四态优先级定案（DATA_GAP > NOT_APPLICABLE > SKIPPED_PRECONDITION > CONFLICT_UNRESOLVED > PASS/FAIL）+ 每态负例要求 |
| P0-4 CONFLICT_UNRESOLVED 无落点 | **已完成**：Finding 增 execution_status（七态含 CONFLICT_UNRESOLVED）与 conflict{sources,resolution,adjudicator}；error_code/expected_status 同步加码；T19 冲突裁决用例 |

### P1（9 项）
| 项 | 修复结果 |
|---|---|
| P1-1 证据等级三轴拆分 | MeasuredParam.confidence_level → source_level/extraction_status/applicability_status 三轴；正式 PASS 三轴同时达标（C 级不再静默 PASS） |
| P1-2 可复现口径+字段 | 同构建逐字节/跨版本容差双口径；AnalysisRun 落 engine_version/unit_dict_version/prompt_version；plugin_ref 增 digest |
| P1-3 容差矛盾 | 改为 |Δ| ≤ max(abs_floor, rel×ref)；Arrhenius 寿命 rel 放宽 0.01 并标模型不确定度 |
| P1-4 矩阵有洞 | 补 FR01/FR11/FR12；修 FR09/T16 错误映射；新增 T17 确定性/T18 覆盖率/T19 冲突裁决 |
| P1-5 0% 漏报口径 | 定为发布门禁条件（非统计结论）；披露置信区间；每域 agreed ≥30 方可计分；disputed 占比披露 |
| P1-6 注入防护输出侧 | 报告渲染禁用远程资源、出站链接域名白名单+审计；语料扩至 28 条 11 形态（output_markdown_remote_resource/output_link_exfiltration/agentic_tool_call/encoding_obfuscation/multi_turn） |
| P1-7 插件无单位 | plugin_ref.params 带 unit+quantity_kind；outputs_exposed 逐项 {name,unit,type,quantity_kind} |
| P1-8 状态词漂移 | 统一以 schema 为准（published）；01/02/模板全部对齐 |
| P1-9 cycles 混装 | cycles 独立维度；lifetime_hours 独立维度；互不转换 |

### P2（10 项）
| 项 | 修复结果 |
|---|---|
| P2-1 Rule 模型漂移 | 01 §5.3 Rule 字段全量对齐 schema（preconditions 数组/tests/curve_eval/plugin_ref/outputs_exposed） |
| P2-2 §5.0 自违反 | calculated_margin/vibration_level 全部 MeasuredParam 化 |
| P2-3 章节顺序+inputs.type | 02 §2.1 调至 §2.2 前；schema inputs 增 type 字段 |
| P2-4 S≥8 映射 | dfmea_scoring_template 增十分制映射（S=9-10↔H、5-8↔M、1-4↔L；AP 制以 AP=Critical 替代） |
| P2-5 组合口径 | 1500 为 V1 基线负载；2000 行硬上限=6000 组合属容量扩展（§5A 已注明） |
| P2-6 领域数 | 13 类修正（8 技术域+5 对抗域）；补规则编写/双审工作量 10-15 人日 |
| P2-7 benchmark 两洞 | resolved 须有非空 adjudication；expected_findings 增 rule_version_at_label 版本化匹配键 |
| P2-8 ReliaTrack 依据 | interface-spec 增代码实查声明与升级触发条件；batch_id 建议改 UUIDv7（登记待办）；CSV BOM 适配待实现时补 |
| P2-9 仓库工程化 | LICENSE（CC BY 4.0）；README 已列附件；docs/legacy/ 三件套 V1.0 原件 + docs/review/ 复审意见全文归档（追溯断链修复）；prompt_injection $schema 改 schema_version |
| P2-10 措辞张力 | 02 §3.1 补「标准强制更严时从标准」 |

### r3 CI 门槛状态（复审 §5 建议）
| 门槛 | 状态 |
|---|---|
| 1. 三模板过 schema 0 error | ✅ 0 errors 实测 |
| 2. 单位字典覆盖模板全部单位 | ✅ ratio/table/degC_per_W/dimensionless 已补；负例（C/H 歧义/cycles/温度混用）已在 normalization_rules 声明，引擎实现时补用例 |
| 3. 温度三用例手算一致 | ✅ 1.00/0.52/0.00 手算值写入模板 notes；absolute/delta 语义已分离 |
| 4. 状态机四负例 | ✅ 状态机定案 + tests 含 SKIPPED_PRECONDITION/NOT_APPLICABLE/DATA_GAP/CONFLICT_UNRESOLVED 各例 |
| 5. tests ≥3 且 kind 覆盖 | ✅ 三模板各 3 条（normal/boundary/invalid） |
| 6. 矩阵补 FR01/FR11/FR12 + T17/T18/T19 | ✅ |
| 7. README 附件清单/LICENSE/追溯链接 | ✅ README 已列；LICENSE=CC BY 4.0；docs/legacy + docs/review 归档 |

## 8. V1.1.1（2026-11-22）：协作者补丁合并轮

来源：协作者独立评审补丁（基于用户上传的旧快照；全文 `REVIEW_REPORT_V1.1.1.md`，结论「有条件通过」）。与本仓 r3（e96955a）平行演进，逐文件三方合并，**未覆写已定案内容**。

### 合并采纳
| 项 | 说明 |
|---|---|
| 附件 dfmea_scoring_template.md | 替换为 27 组合完整 AP 网格版（消除「其余按经验排序」口径漂移；补企业落地要求：O 须映射失率/频次、无数据标 TBD）；保留 §6 十分制映射 |
| 附件 unit_dictionary.yaml | 并入 alias_normalization_rules 强化版：SI 符号大小写敏感（mW/MW 不得折叠）、自然语言别名歧义须显式维度、µ/u/micro 前缀歧义限定、non_physical_types（table 不参与换算） |
| 附件 benchmark.schema.json | 并入 annotations[]（双人独立原始标注逐条保留，不得被共识覆盖——一致性可计算）+ $defs/finding/notExpected；r3 的 rule_version_at_label 已回填 annotations 与 $defs |
| tools/validate_assets.py | **CI 门槛工具化**（复审 §5 建议 1-2、5、7 落地）：schema 自检、模板 0-error、注入语料 ≥20、单位精确别名碰撞检测（含已知歧义白名单 WARN：K/h/小时 跨维度须显式维度）、benchmark 示例校验 |
| tools/requirements-validation.txt | 校验依赖（PyYAML、jsonschema） |
| V1.1/REVIEW_REPORT_V1.1.1.md | 协作者评审报告入库（存档） |
| V1.1/attachments/examples/benchmark_sample.example.json | 基准样本示例（已补 rule_version_at_label） |
| rule_templates.yaml | status published→draft（示意证据不得作为真实证据发布，协作者理由成立）；插件参数补 source/approval 字段 |

### 修复与把关
- 合并后 validate_assets.py 首跑 FAIL 两项，已修：示例补 rule_version_at_label（$defs/finding 同步）；单位精确别名碰撞 K/h/小时 列为已知歧义 WARN（解析须显式维度，字典 normalization_rules 已声明）。
- 把关拒绝项：协作者 rule_templates 基于 r3 前旧快照（无 quantity_kind），未整体替换；status 统一方向取 draft（推翻 r3 的 published，理由=占位证据）。

### 校验状态
validate_assets.py：**PASS**（RULE ×3 PASS、BENCHMARK SAMPLE PASS、INJECTION 28≥20、COLLISIONS 0 + WARN ×3 已知歧义）。

## 10. V1.1.1-r3-delta（2026-11-22）：协作者 delta 复审修复

来源：协作者对 r3 文档层的追加复审（REVIEW/V1.1-ER-r3-delta-review.md，确认 P0-1 已清零、P0-2「只改定义没改样例」仍阻断 + 1 P1 + 4 P2）。
**核心修复**：DSL 字面量单位口径定案（02 §2.1 + engine 实现双落地）——表达式字面量按所在 inputs 的声明单位口径解释（MeasuredParam.decl），模板常量 °C 直觉语义成立；02 §2.1 温度双轨重写（quantity_kind 显式）+ published ≥3 用例门禁（schema if/then）+ 错误码表扩全；01 promote 流转 approved→published、工日按 0.5-1 人日/条区间、README 版本行与容差口径同步、interface-spec batch_id 改 UUIDv7、unit_dictionary 移除单字母 C 别名（charge 冲突）、rule_templates 补 thermal_resistance_ca quantity_kind=delta 与前置边界 <=。
pytest 6 passed + validate_assets PASS。

## 11. G1-r4（2026-11-22）：引擎代码审核修复轮

来源：协作者引擎代码审核（G1引擎与r3-delta代码审核.md，基线 e4a8073）——3 个 P0 契约漂移 + 4 项 P1 + P2 杂项，逐项修复。

### P0（契约漂移）
| 项 | 修复 |
|---|---|
| B-1 DSL 与规范两套语法（AND 大写裸抛 SyntaxError、IF 死代码） | **定案：DSL 采用 Python 语法**（and/or/not + 三元式），02 §2.1 与 rule.schema.json 白名单同步改写；dsl.py ALLOWED_NODES 含 IfExp、Call 一律拒绝；declarative 求值异常全捕获 → ERROR（不再裸抛 SyntaxError） |
| B-2 lookup_curve 只做 1D、curve_eval.expression 不被读取（静默漂移） | **定案：v1 单族 1D 插值**——curve_eval 增 table_columns {x,y}（列名参数化，去硬编码）与 target_var（显式目标变量，去启发式选择）；curve_eval.expression 明确为「人读描述，v1 不执行」（02 §2.2/schema 同步）；多族 2D 留 V2 |
| B-3 §2.1 两口径并存 | 一句话统一：「入库时归一存档（norm_value），求值时按声明口径换算（decl）」 |

### P1
| 项 | 修复 |
|---|---|
| C-1 script_plugin 判定硬编码 ecap 语义 | plugin_ref 增 verdict_expr（DSL 求值，命名空间=inputs+outputs+params）；模板 3 补 verdict_expr |
| C-2 decl() 静默回退 | 换算失败改抛 UnitError（UNKNOWN_UNIT/DIMENSION_MISMATCH），不再拿 norm_value 冒充 |
| C-3 三轴门禁与 digest 未接线 | run_rule 出口检查全部 inputs 三轴（不达标→advisory 标记，PASS 附「仅建议性」）；register_plugin 强制 digest、run_script_plugin 校验 digest 匹配 |
| C-4 依赖未声明 | engine/requirements.txt（PyYAML/jsonschema/pint/simpleeval/pytest） |

### D（P2）
死代码清理（_ExprEnv/未用 import）；precondition DSL 违规→ERROR 分流；normalize degC_delta norm_unit 归 K；表变量判定去名字启发式（按 unit=='table'）；.gitignore 去重；schema 尾换行。

### 测试与校验
pytest 6 passed（含 C-3 advisory 实测：C 级输入 → PASS + advisory 标记）；validate_assets.py PASS（碰撞 0 + 已知歧义 WARN×3）。
G1 标记：**prototype → implementation baseline 候选**（待协作者对 e4a8073+r4 复核确认）。

## 12. G1-r5（2026-11-22）：r4 追加复核修复轮（崩溃回归清零）

来源：协作者对 G1-r4 的追加复核（确认 r4 三项契约漂移修复属实，但 C-2 修复方式引入数字字符串崩溃回归 + SyntaxError 裸抛与 CHANGELOG 声明不符）。全部按复审给出的三处一行级修法执行：
- **P0-C2R**：decl() 数字字符串合法（float(raw_value) 先行——数据管线常态）；非数值抛 INVALID_VALUE（新错误码，替代 MISSING_INPUT 挪用）；_collect 统一包 UnitError → ERROR Finding（带 code），run_rule 不再裸抛。
- **P0-B1R**：dsl.validate 的 ast.parse 包 try → ValueError（SyntaxError 转 ERROR）。
- 残留 P2：02 温度双轨条目与统一口径条目统一（求值按声明口径）；curve_eval.temp_var 显式声明（schema/模板/引擎三处，去名称推断）；validate_assets 增 published 门禁复核（status=published → tests≥3 且 kind 覆盖三类）；.gitignore 去重。
- 回归：新增 4 条崩溃路径用例（数字字符串、55x→ERROR(INVALID_VALUE)、AND→ERROR(DSL)、digest 不匹配→ERROR、verdict_expr 85℃ FAIL）——pytest 10 passed；validate_assets PASS。

## 13. G1-r6（2026-11-22）：化妆级清零 + 测试恢复

- 化妆项全部清理：run_rule 签名移除未使用的 engine 参数、outputs_named 死代码、advisory 重复赋值、ERROR 前缀重复（UnitError str 已含 code）、dsl.py ast.Call 不可达分支、unit_dim 无消费构建、.gitignore 去重。
- schema temp_var 改条件必填（仅温度折减规则要求）。
- 测试恢复与补齐：r4-r6 期间的 rebase/checkout 事故曾致测试文件混乱——从 683c06e 干净基线恢复并重补 4 条崩溃路径回归（数字字符串/55x→INVALID_VALUE/AND→DSL 违规/digest 不匹配/verdict_expr）。pytest **10 passed**。
- validate_assets PASS（published 门禁复核已上线，模板全 draft 故空转——现状如实）。
