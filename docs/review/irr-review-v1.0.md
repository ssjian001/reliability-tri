# reliability-tri · V1.1-ER 实施就绪评审意见（IRR，2026-11-22）

> 存档说明：本文件为 V1.1-ER-r2（commit fcec5ac）的复审意见全文存档，由协作者完成（逐节人工评审 + jsonschema Draft 2020-12 机读实测）。r3 修复针对其中的 P0×4、P1×9、P2×10 逐项执行；复现记录见 CHANGELOG §5。

- 评审对象：https://github.com/ssjian001/reliability-tri（commit fcec5ac，2026-11-22）
- 范围：V1.1/ 三份规格书 + 7 个附件
- 方式：逐节人工评审 + 机读契约实测（jsonschema Draft 2020-12 校验模板、PyYAML 解析、单位/温度手算复核）
- 结论：文档层显著完善，机读契约层不通过。当前不宜保留 Engineering Implementation Ready 标签，建议出 V1.1-ER-r3 后再交开发。

## 0. 一句话结论

三条"标准模板"没有一条能通过自家的 rule.schema.json（实测 39 个校验错误）；叠加温度归一、前置条件、冲突状态三处设计级缺口——照现文档直接实现，规则引擎会在第一批规则上就卡住。

## 1. 阻断项（P0）

### P0-1 模板与 Schema 互相矛盾（实测 39 errors）

复现：对 rule_templates.yaml 三条模板逐条跑 Draft202012Validator(rule.schema.json) → 15 / 12 / 12 个错误，全部不合法。

1. expression 被全局 required，但 description 明确"仅 declarative_expr 必填"；模板 2/3 无顶层 expression。
2. tests.items.required 含未定义的 expected。
3. tests minItems 3，模板分别只有 2/1/1 条。
4. preconditions 类型冲突：schema 为 string，模板为数组。
5. thresholds 形状不符：schema 要求 {value, unit, source_ref}，模板写 default/high_reliability/source。
6. evidence 必填 6 字段，模板只给 {evidence_id, page_or_section}。
7. status: approved 非法（enum 为 draft/in_review/tested/shadow/published/deprecated）。
8. YAML 日期未加引号（PyYAML 解析为 datetime.date）。
9. 单位字典缺 ratio/table/degC_per_W/dimensionless。
10. inputs.source 词表与模板不一致。

### P0-2 温度归一模型自相矛盾

unit_dictionary canonical 是 degC 但 to_si 仿射 +273.15→K，且无 absolute/delta 区分。模板 2 折减因子按 °C 写，若先归一（25℃→298.15）因子变 -1.185，SOA 判定必错。模板 1 的 local_ambient_temp <= 70 同样冲突。
建议：MeasuredParam 增 quantity_kind: absolute|delta；absolute 归一 K、delta 用 K 差值；模板 2 用 K 重写并给出 25/85/150℃ 三组期望因子。

### P0-3 前置条件没有机器可判定语义

02 §2.2 承诺 SKIPPED_PRECONDITION，但 schema preconditions 是人读 string，applicability 只支持字面值匹配，无法表达 <= 70。模板 1 的 85℃ 测试恰恰断言 SKIPPED_PRECONDITION——引擎无从判定。状态优先级（缺数据/不适用/前置不满足/冲突）未定义。

### P0-4 CONFLICT_UNRESOLVED 没有落点

02 §3.1 要求输出该码并阻断放行，但 error_code enum 没有它、Finding 无冲突字段、expected_status 五态不含冲突。规范里最关键的"冲突必须拦截"在数据模型上无法表达。

## 2. 高优先级（P1）

1. A/B/C/D 语义双关：confidence_level 与 Evidence.level 共用字母；§7A 人工确认直接标 "Evidence Level A" 混淆"来源权威"与"数值可信"；C 级可静默 PASS。建议拆三轴（source_level/extraction_status/applicability_status），正式 PASS 三轴同时达标。
2. 可复现性口径过强且字段不全："逐字节一致"跨 build 不现实（浮点）；AnalysisRun 缺 engine_version/unit_dict_version/prompt_version；plugin_ref 无 digest。建议：同镜像逐字节、跨版本按容差；unit_dict_version 用内容哈希。
3. 容差条款自相矛盾："相对误差 ≤0.1% 或绝对误差按更严者"逻辑冲突；0.1% 对 Arrhenius 寿命过紧。建议 |Δ| ≤ max(abs_floor, rel×ref)，按指标类给两列。
4. 验证矩阵有洞：漏 FR01/FR11/FR12；"FR09/T16→T16" 映射错误；新增的确定性/覆盖率/冲突裁决无 T 用例。建议补 FR01/FR11/FR12 + T17/T18/T19。
5. 0% 漏报红线无法统计证明：30-50 样本 0 漏报的 95% 置信上界约 6%；disputed 被排除可稀释分母。建议每域最小 agreed 样本数（≥30）、0% 定义为门禁而非统计结论、披露置信区间。
6. 注入防护只防输入侧：输出侧 markdown 远程资源可自动加载构成外泄与二次注入通道；语料缺 agentic/工具调用、编码混淆、图片 alt/PDF 元数据、多轮诱导。建议"渲染禁用远程资源 + 链接域名白名单 + 出站审计"，语料扩四类。
7. 插件参数与输出裸数无单位：doubling_temp_delta: 10.0、outputs_exposed 无单位；违反 §5.0。建议 params 带 unit，outputs 声明 {name, unit, type}。
8. 状态词表三处漂移：01 写 approved、02 写"批准发布"、schema 用 published。以 schema 为唯一来源。
9. 寿命维度混装：cycles 放进 lifetime（h）维度，互换会静默算错。cycles 独立维度。

## 3. 一般问题（P2）

1. Rule 数据模型与 schema 漂移（01 仍 expression_or_payload/test_cases，无 tests/curve_eval/plugin_ref/outputs_exposed）。
2. §5.0 被自己违反：Finding.calculated_margin、OperatingProfile.vibration_level 仍是裸值。
3. 章节顺序：02 §2.2 排在 §2.1 之前；inputs 缺 type 字段。
4. S≥8 无映射：默认模板只有 H/M/L 三档，需给映射或注明条件适用十分制。
5. 规模数字：500×3=1500 vs 硬上限 2000 行意味着 6000 组合，未说明分批；P95 无参考硬件/样本量/冷热缓存口径，未含 LLM 耗时。
6. "8 领域" vs benchmark.schema domain 13 类；01 未估 ≥60 条规则的编写/测试/双审工作量。
7. benchmark 两洞：resolved 允许 adjudication 为 null；匹配只按 risk_ref，规则改版后基准集失效。
8. ReliaTrack 依据不可核：未给 commit/hash 与 DDL 摘录；batch_id=时间戳+行数易碰撞（建议 UUIDv7）；CSV 供 Excel 需 UTF-8 BOM。
9. 仓库工程化：README 未列 7 个附件；无 LICENSE；CHANGELOG 承认追溯断链；prompt_injection_dataset 的 $schema 指向元 schema 被工具误判。
10. 措辞张力：02 §3.1 规则 1 与硬约束 5 需加"标准强制更严时从标准"。

## 4. 做得好的地方

- IRR 12 项逐项落点表，评审闭环可追踪；
- 三类执行器边界清楚（DSL/插值/受控插件），把 LLM 挡在数值计算之外；
- MeasuredParam 保留原值 + T03 用例，方向正确；
- Datasheet 抽取"未确认即 D 级、禁用于正式判定"的防呆设计；
- 基准集双人标注 + 第三方仲裁；标准文本只存元数据，版权合规；
- ReliaTrack 不硬造 REST API、改走批量交换，是务实的取舍。

## 5. 建议纳入 r3 的验收门槛（可直接进 CI）

1. make validate：三条模板过 schema 0 error；YAML 日期全为 string。
2. 单位字典覆盖模板全部单位；负例覆盖 C/H 歧义、cycles、温度混用。
3. 温度三用例（25/85/150℃）因子与手算一致；absolute/delta 各 1 例。
4. 状态机四负例：缺数据、不适用、前置不满足、来源冲突。
5. 每条规则 tests ≥3 且 kind 覆盖 normal/boundary/invalid。
6. 03 矩阵补 FR01/FR11/FR12 + T17/T18/T19。
7. README 附件清单、LICENSE、CHANGELOG 追溯链接补齐。
