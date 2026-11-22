# G1 — Deterministic Rule Engine MVP

**Status:** implemented as an executable reference implementation; production hardening remains subject to G6/G8.

## 1. Scope and non-goals

G1 implements the deterministic execution boundary for three rule types: `expression`, `lookup_curve`, and `script_plugin`. It does not implement rule lifecycle/approval workflows, persistence, API service, distributed execution, audit database, or the ReliaTrack integration. Those belong to later gates (G2/G3/G7/G8).

## 2. Expression DSL

### Grammar

```text
expression := or_expr
or_expr    := and_expr ("or" and_expr)*
and_expr   := compare ("and" compare)*
compare    := sum (("<"|"<="|">"|">="|"=="|"!=") sum)?
sum        := product (("+"|"-") product)*
product    := power (("*"|"/") power)*
power      := unary ("**" unary)?
unary      := ("+"|"-"|"not") unary | primary
primary    := number ["[" unit "]"] | identifier | "null" | function_call | "(" expression ")"
function_call := ("min"|"max") "(" expression ("," expression)+ ")"
               | "abs" "(" expression ")"
               | "lookup_max_id" "(" table_id "," expression "," expression ")"
```

The parser creates a tuple-based AST and the evaluator interprets only AST node types emitted by this parser. It never calls `eval`, `exec`, imports, attribute access, indexing, assignments, loops, comprehensions, or user-defined functions. Allowed generic functions: `min`, `max`, `abs`. `lookup_max_id` is only enabled by the `lookup_curve` executor through an injected, versioned CurveRepository callback; it is unavailable to normal expression rules.

### Resource limits

- Maximum expression length: 4096 characters.
- Maximum token count: 512.
- Numeric quantities must be finite.
- Exponents: integer from -3 to 3; dimensional quantity exponentiation is restricted to exponent 1.
- No arbitrary recursion or user callbacks are exposed by the DSL.

### Example

```text
local_ambient_temp <= 70[degC] and junction_temp <= 125[degC]
```

Inputs use `{ "value": 65, "unit": "degC" }`. A missing input returns `INPUT_MISSING`; incompatible dimensions return `DIMENSION_MISMATCH`.

## 3. Unit semantics

- SI unit symbols are case-sensitive. `mW` is milliwatt; `MW` is not an alias and is rejected.
- Absolute temperature is canonicalized to kelvin. `degC` and `degF` use affine conversion.
- `temperature_difference` is a separate dimension (`deltaK`, `deltaC`). Absolute temperature cannot be added to another absolute temperature or multiplied/divided.
- Addition and comparison require compatible dimensions. Subtracting two absolute temperatures returns a temperature difference. `C` is coulomb (charge), not Celsius; Celsius must be written `degC`.
- The implementation supports a deliberately bounded unit set in `units.py`. Before adding a unit, add conversion and dimensional tests; do not infer units by case folding.

## 4. Curve lookup

Two curve execution paths are implemented:

1. Simple 1D `curve` payload: piecewise-linear interpolation. X coordinates must be strictly increasing and X/Y dimensions consistent. Extrapolation is explicit: `error` (default), `clamp`, or `linear`.
2. Schema-style `curve_eval`: a registered 2D rectangular grid is queried through `lookup_max_id(table_id, x, y)`. `linear` uses bilinear interpolation; `log_log_linear` uses bilinear interpolation in log(x), log(y), log(z) space and requires positive grid values. `curve_out_of_bounds` is `error` or `clamp`.

The 2D implementation is a mathematical reference method. It does not prove that a vendor SOA curve should be digitized/interpolated in log-log space; the interpolation method, digitization uncertainty, datasheet source and curve checksum must be validated per component family before a production rule is published.

## 5. Plugin execution boundary

Rule payloads contain only a `plugin_ref`; they cannot contain executable source. Plugins must be registered in a trusted deployment-side registry, approved, and marked as sandboxed. Invocation uses `subprocess.run` with `shell=False`, a clean environment, working directory `/`, JSON-only stdin/stdout, timeouts, and input/output size caps.

**Critical deployment requirement:** `sandboxed=True` is a trusted administrator assertion, not an OS sandbox implementation. Production must configure the executable as an OS-enforced sandbox launcher/profile (container, bubblewrap, firejail, or equivalent) that denies network by default, limits filesystem access, drops privileges, and caps CPU/memory/processes. If that deployment control cannot be demonstrated, do not register production plugins. The unit tests use a local echo process only to test protocol handling; they do not certify sandbox isolation.

## 6. Rule execution result contract

Every call returns a stable object with `rule_id`, `status`, `result`, and `error_code`; statuses are `pass`, `fail`, or `error`. An expression rule must evaluate to boolean. Exceptions are converted to stable error codes and do not become an implicit pass.

## 7. Run locally

```bash
python -m pip install -e .
python -m unittest discover -s tests/g1 -v
reliability-rule-run examples/g1/rule_examples.json
```

Without installing the package:

```bash
PYTHONPATH=src python -m unittest discover -s tests/g1 -v
PYTHONPATH=src python -m reliability_engine.cli examples/g1/rule_examples.json
```

## 8. G1 acceptance record

Automated tests cover parser rejection, missing inputs, unit conversion, dimension mismatch, absolute-temperature semantics, boolean evaluation, curve interpolation/boundaries/out-of-range/ordering, rule dispatch, and plugin approval/sandbox flags/protocol. Passing this suite verifies the reference implementation only. Before production acceptance, add property-based/fuzz tests, independent security review, plugin sandbox proof, performance baselines, and integration tests against the actual rule schema/API (G2/G6).
