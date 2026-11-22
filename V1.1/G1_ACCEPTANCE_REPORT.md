# G1 规则执行引擎阶段验收报告

- 版本：G1 Engine MVP 0.1.0
- 日期：2026-11-22
- 验收对象：V1.1.1 规格与附件基础上的 G1 可执行参考实现
- 结论：**代码级验收通过；生产部署验收有条件通过**

## 1. 交付范围

| G1 工作包 | 实现内容 | 验收状态 |
|---|---|---|
| DSL Parser / AST | 受限词法/语法解析、AST 解释器、白名单运算符与函数、表达式长度/Token 限制 | PASS |
| Unit Engine | 大小写敏感 SI 符号、显式别名、SI/仿射温度换算、绝对温度/温差分离、复合量纲运算 | PASS |
| expression 执行器 | `declarative_expr` / `expression`，前置条件、缺失输入、单位和布尔判定 | PASS |
| lookup_curve 执行器 | 1D 分段线性插值；2D 网格 bilinear / log-log bilinear；边界 error/clamp；温度折减和安全系数表达式 | PASS（算法参考实现） |
| script_plugin 执行器 | 注册表、审批门禁、JSON 协议、超时、输入/输出大小限制、错误状态和输出字段校验 | PASS（适配器） |
| 示例与文档 | CLI、示例规则、语法/量纲/曲线/插件安全边界说明 | PASS |

## 2. 自动化验证结果

运行命令：

```bash
PYTHONPATH=src python -m unittest discover -s tests/g1 -v
PYTHONPATH=src python -m reliability_engine.cli examples/g1/rule_examples.json
python tools/validate_assets.py
```

结果：

- G1 单元测试：**33 / 33 PASS**。
- CLI 示例：expression 规则 PASS；1D curve 规则 PASS，插值结果 0.7 Ohm。
- V1.1.1 资产校验：3 条规则模板 PASS、benchmark sample PASS、Prompt Injection 数据集 22 项、单位精确别名冲突 0 项。
- Python 编译检查：PASS。

覆盖的测试类别：表达式白名单与非法语法、单位别名/倍率/温度换算、复合量纲、缺失输入、量纲冲突、绝对温度运算限制、布尔逻辑、曲线插值/边界/越界/温度折减、三类规则分派、插件未登记/未审批/未沙箱、超时、输出大小限制及 Schema 风格 plugin_ref。

## 3. 与 V1.1.1 规则结构的衔接

- `declarative_expr` 对应规则模板中的表达式规则类型；执行时按 `inputs[].unit` 将裸数值归一为带量纲 Quantity。
- `lookup_curve` 支持 Schema 的 `curve_eval` 配置，`lookup_max_id(table_id, x, y)` 由受控 CurveRepository 注入；曲线表需在服务启动/数据装载阶段注册。
- `script_plugin` 支持 Schema 的 `plugin_ref.module` + `entry_func`，注册键为 `module::entry_func`；`params` 随 JSON payload 传递。
- `preconditions` 不满足时返回 `skipped / PRECONDITION_NOT_MET`；不得将跳过误报为 PASS。

## 4. 生产化前置条件（不得忽略）

1. **OS 沙箱证明**：代码中的 `sandboxed=True` 是受信任部署注册表的配置声明，不是 Python 自身创建的安全边界。生产插件必须通过经验证的 bwrap/Firejail/容器等 OS 沙箱启动，默认禁网、只读文件系统、最小挂载、非特权用户、CPU/内存/PID 限制，并通过 G6 红队测试。未提供部署证明前，不得将任何插件注册为生产可执行插件。
2. **曲线算法适用性**：2D `log_log_linear` 是数值算法实现，不等于所有厂商 SOA 曲线都适合双对数双线性插值。每条曲线必须保留原始 datasheet、页码、数字化方法、坐标校准、checksum、插值策略和不确定度；需要专家确认后发布。
3. **单位覆盖率**：引擎已实现项目中列明的常用单位与显式别名，但不是 Pint 全量替代品。新增单位/别名必须先补量纲定义和测试，不能自动猜单位。
4. **性能与模糊测试**：当前为功能正确性测试，不构成 P95/P99 性能承诺；仍需 G5 固定环境压测和 G6 fuzz / red-team。
5. **API / 数据持久化**：本阶段未实现 REST API、OpenAPI、数据库持久化、规则版本服务、审计事件库或并发任务队列，属于 G2/G8。

## 5. G1 退出判断

G1 的确定性执行核心已具备可运行代码和回归测试，可进入 G2 接口与数据契约阶段。插件 OS 沙箱实际部署验证、曲线数字化质量验证和性能/安全专项验证必须保留为后续门禁，不得因本报告的代码级 PASS 自动关闭。
