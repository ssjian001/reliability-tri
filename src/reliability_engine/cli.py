import argparse, json
from pathlib import Path
from .executor import RuleExecutor

def main():
    ap=argparse.ArgumentParser(description="Run a reliability rule fixture (G1 engine MVP)")
    ap.add_argument("fixture", help="JSON file containing an array of rule fixtures")
    args=ap.parse_args()
    data=json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    if not isinstance(data,list): ap.error("Fixture root must be a JSON array")
    engine=RuleExecutor(); results=[]
    for item in data:
        results.append(engine.execute(item,{k:v for k,v in item.get("inputs",{}).items()}))
    print(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False))
    return 1 if any(x["status"] in ("fail","error") for x in results) else 0

if __name__=="__main__": raise SystemExit(main())
