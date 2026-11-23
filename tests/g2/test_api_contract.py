import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from reliability_api.main import create_app
from reliability_api.db import Base

RULE={
 "rule_id":"ELEC-RES-PWR-001","rule_type":"declarative_expr","domain":"derating",
 "title":"Resistor power derating check","intent":"Check steady-state resistor power ratio",
 "applicability":{"component_category":"Resistor"},
 "inputs":[{"name":"power_dissipation","unit":"W","required":True,"source":"ComponentStress"},{"name":"rated_power_70c","unit":"W","required":True,"source":"Datasheet"},{"name":"derating_ratio_limit","unit":"ratio","required":True,"source":"Thresholds"}],
 "expression":"(power_dissipation / rated_power_70c) <= derating_ratio_limit",
 "severity":"high","rationale":"Excess dissipation can accelerate drift.","recommendation":"Select a higher-rated part.",
 "evidence_level":"D","evidence":[{"evidence_id":"EVD-TEST-001","level":"D","publisher":"Test fixture","title":"Test-only placeholder evidence","version_date":"2026-11-23","locator":"fixture"}],
 "owner":"Reliability","reviewer":"Reviewer","version":"1.0.0","status":"draft","effective_date":"2026-11-23",
 "tests":[{"name":"normal pass","kind":"normal","inputs":{"power_dissipation":0.04,"rated_power_70c":0.1,"derating_ratio_limit":0.5},"expected_status":"PASS"},{"name":"boundary pass","kind":"boundary","inputs":{"power_dissipation":0.05,"rated_power_70c":0.1,"derating_ratio_limit":0.5},"expected_status":"PASS"},{"name":"fail","kind":"invalid","inputs":{"power_dissipation":0.06,"rated_power_70c":0.1,"derating_ratio_limit":0.5},"expected_status":"FAIL"}]
}

def client():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return TestClient(create_app(database_engine=engine))

def test_rule_lifecycle_and_analysis():
    c=client()
    r=c.post("/v1/rules",json={"definition":RULE},headers={"X-Actor-ID":"tester"})
    assert r.status_code==201, r.text
    body=r.json(); assert body["status"]=="draft"
    rid=body["rule_id"]; version_id=body["version_id"]
    assert c.get("/v1/rules/"+rid).status_code==200
    tested=c.post(f"/v1/rules/{rid}:test",json={"inputs":{"power_dissipation":0.04,"rated_power_70c":0.1,"derating_ratio_limit":0.5}})
    assert tested.status_code==200 and tested.json()["execution"]["status"]=="pass"
    validation=c.post(f"/v1/rules/{rid}:validate")
    assert validation.status_code==200 and validation.json()["all_passed"] is True
    approval=c.post("/v1/approvals",json={"target_type":"rule_version","target_id":version_id,"action":"publish","decision":"approved"})
    assert approval.status_code==201 and approval.json()["rule_status"]=="published"
    run=c.post("/v1/analyses/derating",json={"inputs":{"power_dissipation":0.06,"rated_power_70c":0.1,"derating_ratio_limit":0.5}},headers={"Idempotency-Key":"derating-run-0001"})
    assert run.status_code==200, run.text
    run_id=run.json()["run_id"]
    assert run.json()["summary"]["counts"]["fail"]==1
    replay=c.post("/v1/analyses/derating",json={"inputs":{"power_dissipation":0.06,"rated_power_70c":0.1,"derating_ratio_limit":0.5}},headers={"Idempotency-Key":"derating-run-0001"})
    assert replay.status_code==200 and replay.json()["run_id"]==run_id
    conflict=c.post("/v1/analyses/derating",json={"inputs":{"power_dissipation":0.04,"rated_power_70c":0.1,"derating_ratio_limit":0.5}},headers={"Idempotency-Key":"derating-run-0001"})
    assert conflict.status_code==409
    findings=c.get(f"/v1/analyses/{run_id}/findings")
    assert findings.status_code==200 and findings.json()["total"]==1

def test_rule_version_is_immutable_and_unique():
    c=client()
    created=c.post("/v1/rules",json={"definition":RULE})
    assert created.status_code==201
    rid=created.json()["rule_id"]
    next_definition={**RULE,"version":"1.0.1"}
    newer=c.post(f"/v1/rules/{rid}/versions",json={"definition":next_definition})
    assert newer.status_code==201 and newer.json()["version"]=="1.0.1"
    duplicate=c.post(f"/v1/rules/{rid}/versions",json={"definition":next_definition})
    assert duplicate.status_code==409


def test_invalid_rule_contract_rejected():
    c=client()
    r=c.post("/v1/rules",json={"definition":{"rule_id":"bad"}})
    assert r.status_code==422
    assert r.json()["detail"]["error_code"]=="RULE_SCHEMA_INVALID"

def test_health_and_openapi():
    c=client()
    assert c.get("/health").json()["status"]=="ok"
    spec=c.get("/openapi.json").json()
    assert spec["openapi"].startswith("3.1") or spec["openapi"].startswith("3.0")
    assert "/v1/analyses/derating" in spec["paths"]

def test_curve_requires_independent_approval():
    import hashlib
    c=client()
    data={"id":"MOSFET-SOA-TEST","x_unit":"V","y_unit":"A","z_unit":"W","x_values":[1.0,2.0],"y_values":[1.0,2.0],"z_values":[[1.0,2.0],[2.0,4.0]],"interpolation":"log_log_linear","source_ref":"datasheet.pdf#page=4"}
    canonical=json.dumps({k:v for k,v in data.items() if k!="source_ref"},sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    data["checksum"]=hashlib.sha256(canonical).hexdigest()
    created=c.post("/v1/curves",json=data,headers={"X-Actor-ID":"curve-author"})
    assert created.status_code==201, created.text
    target=created.json()["curve_id"]
    self_approval=c.post("/v1/approvals",json={"target_type":"curve","target_id":target,"action":"publish","decision":"approved"},headers={"X-Actor-ID":"curve-author"})
    assert self_approval.status_code==403
    approved=c.post("/v1/approvals",json={"target_type":"curve","target_id":target,"action":"publish","decision":"approved"},headers={"X-Actor-ID":"independent-reviewer"})
    assert approved.status_code==201 and approved.json()["curve_approved"] is True

def test_api_key_gate(monkeypatch):
    from reliability_api.config import settings
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings,"api_key","test-secret")
    c=TestClient(create_app(database_engine=engine))
    assert c.get("/v1/rules").status_code==401
    assert c.get("/v1/rules",headers={"Authorization":"Bearer test-secret"}).status_code==200


def test_publish_blocked_until_rule_test_suite_passes():
    c=client()
    created=c.post("/v1/rules",json={"definition":RULE}).json()
    blocked=c.post("/v1/approvals",json={"target_type":"rule_version","target_id":created["version_id"],"action":"publish","decision":"approved"})
    assert blocked.status_code==409
    assert blocked.json()["detail"]["error_code"]=="RULE_TEST_GATE_REQUIRED"
