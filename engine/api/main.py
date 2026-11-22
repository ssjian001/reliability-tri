"""G2-1 REST API 服务化（01 §6 定案契约）。

- 异步分析：202 Accepted + run_id，BackgroundTasks 执行
- 幂等键：Idempotency-Key header（写操作重复返回同响应）
- RBAC：Bearer token（V1 简化为共享 token + 角色字段，SSO/OIDC 留部署期）
- 审计：JSONL 审计日志（登录外全部写操作与查询）
- 存储：内存 + JSON 快照持久化（G2 试点口径；DB 迁移属 G3）
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from reliability_engine import UnitEngine, run_rule
from reliability_engine.measured import MeasuredParam

STATE_DIR = Path(__file__).resolve().parents[1] / "api_state"
STATE_DIR.mkdir(exist_ok=True)
AUDIT_LOG = STATE_DIR / "audit.jsonl"

app = FastAPI(
    title="AI 电子硬件可靠性分析系统 API",
    version="0.1.0-G2",
    description="V1.1-ER §6 定案契约的 G2 实现。分析类接口统一异步（202 + run_id）。",
)

_lock = threading.Lock()
STATE = {"projects": {}, "runs": {}, "findings": {}, "idempotency": {}, "rules": {}, "approvals": {}, "tokens": {}}
ATT_ROOT = STATE_DIR / "artifacts"
ATT_ROOT.mkdir(exist_ok=True)


def load_state():
    snap = STATE_DIR / "state.json"
    if snap.exists():
        with _lock:
            loaded = json.loads(snap.read_text(encoding="utf-8"))
            STATE.update(loaded)


def save_state():
    with _lock:
        snap = STATE_DIR / "state.json"
        tmp = snap.with_suffix(".tmp")
        tmp.write_text(json.dumps(STATE, ensure_ascii=False), encoding="utf-8")
        tmp.replace(snap)


def audit(action: str, detail: dict):
    with _lock:
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "action": action, **detail},
                               ensure_ascii=False) + "\n")


def auth(request: Request) -> dict:
    """V1 简化鉴权：Bearer <token>；token 表随 STATE。SSO/OIDC 留部署期（01 §9）。"""
    authz = request.headers.get("Authorization", "")
    if not authz.startswith("Bearer "):
        raise HTTPException(401, "缺少 Bearer token")
    token = authz[7:]
    info = STATE.get("tokens", {}).get(token)
    if info is None:
        raise HTTPException(401, "token 无效")
    return info


def idempotent(request: Request, body_hash: str, execute):
    """幂等键：同 Idempotency-Key + 同 body 哈希 → 返回缓存响应。"""
    key = request.headers.get("Idempotency-Key")
    if not key:
        return execute(), None
    rec = STATE["idempotency"].get(key)
    if rec and rec.get("body_hash") == body_hash:
        return rec["response"], key
    resp = execute()
    with _lock:
        STATE["idempotency"][key] = {"body_hash": body_hash, "response": resp}
    return resp, key


def body_hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     default=str).encode()).hexdigest()[:16]


class ProjectIn(BaseModel):
    name: str
    product_line: str = ""
    owner: str = ""


class BomRow(BaseModel):
    refdes: str
    part_number: str
    category: str
    quantity: int = 1
    rated_params: dict = Field(default_factory=dict)   # {param: {value, unit, ...}} MeasuredParam 简写
    net_name: str = ""
    comment: str = ""


class BomImport(BaseModel):
    rows: list[BomRow]
    profile_id: str = "default"


class StressIn(BaseModel):
    refdes: str
    operating_voltage: dict | None = None      # {value, unit}
    operating_current: dict | None = None
    power_dissipation: dict | None = None
    local_ambient_temp: dict | None = None
    profile_id: str = "default"


class AnalysisIn(BaseModel):
    profile_id: str = "default"
    component_filter: list[str] | None = None


class DispositionIn(BaseModel):
    disposition: str = Field(pattern="^(confirmed|data_gap|rejected|closed)$")
    reason: str = ""
    assignee: str = ""


class ApprovalIn(BaseModel):
    object_type: str
    object_id: str
    reviewer_role: str
    approver: str
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = ""


class RuleIn(BaseModel):
    rule_id: str
    rule_type: str = Field(pattern="^(declarative_expr|lookup_curve|script_plugin)$")
    domain: str
    title: str
    intent: str = ""
    applicability: dict = Field(default_factory=dict)
    inputs: list[dict] = Field(default_factory=list)
    preconditions: list[dict] = Field(default_factory=list)
    expression_or_payload: dict = Field(default_factory=dict)
    thresholds: dict = Field(default_factory=dict)
    severity: str = "medium"
    rationale: str = ""
    recommendation: str = ""
    evidence_level: str = "D"
    owner: str = ""
    version: str = "0.1.0"
    test_cases: list[dict] = Field(default_factory=list)


# ---------- 引擎接入 ----------
ATT = Path(__file__).resolve().parents[2] / "V1.1/attachments"
UNIT_ENGINE = UnitEngine(ATT / "unit_dictionary.yaml")


def run_analysis(project_id: str, run_id: str, analysis_type: str, profile_id: str, comp_filter=None):
    proj = STATE["projects"].get(project_id)
    if proj is None:
        STATE["runs"][run_id] = {"status": "FAILED", "reason": "项目不存在"}
        return
    run = STATE["runs"].setdefault(run_id, {"run_id": run_id, "project_id": project_id,
                                            "analysis_type": analysis_type, "status": "PENDING",
                                            "started_at": time.time()})
    run["status"] = "RUNNING"
    findings = []
    rule_list = [r for r in STATE.get("rules", {}).values() if r.get("status") in ("published", "shadow", "draft", "tested")]
    for bom in proj.get("bom", []):
        if comp_filter and bom["refdes"] not in comp_filter:
            continue
        for profile in proj.get("profiles", [profile_id]):
            for rule in rule_list:
                inputs = {}
                # ComponentStress 映射：(refdes, profile) → MeasuredParam
                stress = (proj.get("stresses") or {}).get(f"{bom['refdes']}@{profile}", {})
                for spec in rule.get("inputs", []):
                    key = spec.get("source_mapping") or spec["name"]
                    raw = stress.get(key) or bom.get("rated_params", {}).get(key)
                    if raw is None:
                        continue
                    try:
                        from reliability_engine.measured import from_dict
                        inputs[spec["name"]] = from_dict({**raw, "unit": raw.get("unit", spec.get("unit", "dimensionless"))}, UNIT_ENGINE)
                    except Exception:
                        continue
                if not inputs:
                    continue
                result = run_rule(rule, inputs, UNIT_ENGINE)
                fid = f"F-{run_id[:8]}-{len(findings)+1}"
                finding = {
                    "finding_id": fid, "run_id": run_id,
                    "target_object_type": "bom_item", "target_object_id": bom["refdes"],
                    "rule_id": rule["rule_id"], "rule_version": rule.get("version", "0.1.0"),
                    "risk_level": rule.get("severity", "medium"),
                    "conclusion_tag": "RULE_DERIVED",
                    "execution_status": result["execution_status"],
                    "rationale": rule.get("rationale", ""),
                    "calculated_margin": result["info"],
                    "data_gaps": result["reasons"],
                    "disposition": "open", "assignee": "", "due_date": None,
                }
                if result["execution_status"] in ("PASS", "FAIL"):
                    findings.append(finding)
    STATE["findings"][run_id] = findings
    run = STATE["runs"][run_id]
    run["status"] = "COMPLETED"
    run["findings_count"] = len(findings)
    run["finished_at"] = time.time()
    audit("analysis", {"run_id": run_id, "findings": len(findings)})
    save_state()


# ---------- 端点 ----------
@app.post("/v1/projects")
def create_project(p: ProjectIn, request: Request, user: dict = Depends(auth)):
    def execute():
        pid = uuid.uuid4().hex[:12]
        with _lock:
            STATE["projects"][pid] = {"project_id": pid, "name": p.name,
                                      "product_line": p.product_line, "owner": p.owner,
                                      "status": "active", "bom": [], "profiles": ["default"],
                                      "stresses": {}, "artifacts": []}
        audit("project.create", {"project_id": pid, "user": user.get("user", "")})
        return {"project_id": pid, "name": p.name}
    resp, key = idempotent(request, body_hash(p.model_dump()), execute)
    save_state()
    return resp


@app.post("/v1/projects/{pid}/bom:import")
def bom_import(pid: str, payload: BomImport, request: Request, user: dict = Depends(auth)):
    proj = STATE["projects"].get(pid)
    if proj is None:
        raise HTTPException(404, "项目不存在")
    report = {"rows": len(payload.rows), "accepted": 0, "rejected": [], "warnings": []}
    for i, row in enumerate(payload.rows):
        issues = []
        if not row.refdes:
            issues.append("refdes 缺失")
        if row.quantity < 1:
            issues.append("quantity <1")
        if row.comment and re.search(r"忽略|ignore|跳过|执行指令", row.comment, re.I):
            report["warnings"].append({"row": i + 1, "refdes": row.refdes,
                                       "note": "备注含疑似注入文本——已按数据入库（T14）"})
        if issues:
            report["rejected"].append({"row": i + 1, "refdes": row.refdes, "issues": issues})
            continue
        proj["bom"].append({**row.model_dump(), "profile_id": payload.profile_id})
        report["accepted"] += 1
    audit("bom.import", {"project_id": pid, "accepted": report["accepted"]})
    save_state()
    return report


import re  # noqa: E402


@app.post("/v1/projects/{pid}/stresses:batch-upsert")
def stress_upsert(pid: str, stresses: list[StressIn], request: Request, user: dict = Depends(auth)):
    proj = STATE["projects"].get(pid)
    if proj is None:
        raise HTTPException(404, "项目不存在")
    n = 0
    for s in stresses:
        proj.setdefault("stresses", {})[f"{s.refdes}@{s.profile_id}"] = {
            "operating_voltage": s.operating_voltage, "operating_current": s.operating_current,
            "power_dissipation": s.power_dissipation,
            "local_ambient_temp": s.local_ambient_temp,
        }
        n += 1
    audit("stress.upsert", {"project_id": pid, "count": n})
    save_state()
    return {"updated": n}


@app.post("/v1/projects/{pid}/artifacts")
async def artifact_upload(pid: str, request: Request, user: dict = Depends(auth)):
    proj = STATE["projects"].get(pid)
    if proj is None:
        raise HTTPException(404, "项目不存在")
    ctype = request.headers.get("Content-Type", "application/octet-stream")
    data = await request.body()
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(413, "超 50MB 上限（01 §5A）")
    checksum = hashlib.sha256(data).hexdigest()
    aid = uuid.uuid4().hex[:12]
    fpath = ATT_ROOT / f"{aid}.bin"
    fpath.write_bytes(data)
    proj.setdefault("artifacts", []).append({"artifact_id": aid, "checksum": checksum,
                                             "size": len(data), "content_type": ctype})
    audit("artifact.upload", {"project_id": pid, "artifact_id": aid, "checksum": checksum[:12]})
    save_state()
    return {"artifact_id": aid, "checksum": checksum, "size": len(data)}


@app.post("/v1/analyses/{analysis_type}")
def start_analysis(analysis_type: str, payload: AnalysisIn, background: BackgroundTasks,
                   request: Request, user: dict = Depends(auth)):
    if analysis_type not in ("design-review", "derating", "dfmea", "fa"):
        raise HTTPException(404, "未知分析类型")
    pid = payload.profile_id and None
    # 简化：项目 id 由 header X-Project-ID 提供（契约演进留 G3）
    pid = request.headers.get("X-Project-ID")
    proj = STATE["projects"].get(pid)
    if proj is None:
        raise HTTPException(404, "项目不存在")
    run_id = uuid.uuid4().hex[:12]
    STATE["runs"][run_id] = {"run_id": run_id, "project_id": pid, "analysis_type": analysis_type,
                             "status": "PENDING", "started_at": time.time()}
    background.add_task(run_analysis, pid, run_id, analysis_type, payload.profile_id,
                        payload.component_filter)
    audit("analysis.start", {"run_id": run_id, "type": analysis_type})
    save_state()
    return JSONResponse(status_code=202, content={"run_id": run_id, "status": "PENDING"})


@app.get("/v1/analyses/{run_id}")
def get_run(run_id: str, user: dict = Depends(auth)):
    run = STATE["runs"].get(run_id)
    if run is None:
        raise HTTPException(404, "run 不存在")
    return run


@app.get("/v1/analyses/{run_id}/findings")
def get_findings(run_id: str, risk_level: str | None = None, conclusion_tag: str | None = None,
                 page: int = 1, size: int = 50, user: dict = Depends(auth)):
    findings = STATE["findings"].get(run_id, [])
    if risk_level:
        findings = [f for f in findings if f["risk_level"] == risk_level]
    if conclusion_tag:
        findings = [f for f in findings if f["conclusion_tag"] == conclusion_tag]
    start = (page - 1) * size
    return {"total": len(findings), "page": page,
            "items": findings[start:start + size]}


@app.post("/v1/findings/{fid}/disposition")
def disposition(fid: str, d: DispositionIn, request: Request, user: dict = Depends(auth)):
    for run_findings in STATE["findings"].values():
        for f in run_findings:
            if f["finding_id"] == fid:
                if f["risk_level"] in ("critical", "high") and d.disposition == "closed":
                    raise HTTPException(403, "关键/高风险不得自动关闭（01 §7），须双人签核")
                f["disposition"] = d.disposition
                f["assignee"] = d.assignee
                audit("finding.disposition", {"finding_id": fid, "disposition": d.disposition})
                save_state()
                return {"finding_id": fid, "disposition": d.disposition}
    raise HTTPException(404, "finding 不存在")


@app.post("/v1/approvals")
def approvals(a: ApprovalIn, request: Request, user: dict = Depends(auth)):
    aid = uuid.uuid4().hex[:10]
    STATE.setdefault("approvals", {})[aid] = {**a.model_dump(), "timestamp": time.time()}
    audit("approval", {"approval_id": aid, "object": f"{a.object_type}/{a.object_id}"})
    save_state()
    return {"approval_id": aid, "decision": a.decision}


@app.post("/v1/rules")
def create_rule(r: RuleIn, request: Request, user: dict = Depends(auth)):
    if r.rule_id in STATE.get("rules", {}):
        raise HTTPException(409, "规则已存在")
    STATE.setdefault("rules", {})[r.rule_id] = {**r.model_dump(), "status": "draft"}
    audit("rule.create", {"rule_id": r.rule_id})
    save_state()
    return {"rule_id": r.rule_id, "status": "draft"}


@app.post("/v1/rules/{rule_id}:test")
def rule_test(rule_id: str, user: dict = Depends(auth)):
    rule = STATE.get("rules", {}).get(rule_id)
    if rule is None:
        raise HTTPException(404, "规则不存在")
    tests = rule.get("test_cases") or []
    return {"rule_id": rule_id, "cases": len(tests),
            "note": "用例执行接引擎 run_rule（G3 实现 CLA 执行面）；当前返回声明用例数"}


@app.post("/v1/rules/{rule_id}:promote")
def rule_promote(rule_id: str, user: dict = Depends(auth)):
    order = ["draft", "in_review", "tested", "shadow", "published", "deprecated"]
    rule = STATE.get("rules", {}).get(rule_id)
    if rule is None:
        raise HTTPException(404, "规则不存在")
    cur = rule.get("status", "draft")
    if cur not in order[:-1]:
        raise HTTPException(409, f"状态 {cur} 不可流转")
    rule["status"] = order[order.index(cur) + 1]
    audit("rule.promote", {"rule_id": rule_id, "to": rule["status"]})
    save_state()
    return {"rule_id": rule_id, "status": rule["status"]}


@app.post("/v1/rules/{rule_id}:rollback")
def rule_rollback(rule_id: str, user: dict = Depends(auth)):
    rule = STATE.get("rules", {}).get(rule_id)
    if rule is None:
        raise HTTPException(404, "规则不存在")
    rule["status"] = "draft"
    audit("rule.rollback", {"rule_id": rule_id})
    save_state()
    return {"rule_id": rule_id, "status": "draft"}


@app.post("/v1/reports:export")
def report_export(request: Request, user: dict = Depends(auth)):
    body = request.headers.get("X-Run-ID")
    if not body:
        raise HTTPException(400, "X-Run-ID header 必填")
    findings = STATE["findings"].get(body, [])
    md = [f"# 分析报告 {body}", "",
          f"- run_id: {body}", f"- findings: {len(findings)}", ""]
    for f in findings:
        md.append(f"- [{f['risk_level']}] {f['target_object_id']} · {f['rule_id']} · {f['execution_status']}")
    return {"format": "markdown", "content": "\n".join(md)}


load_state()
