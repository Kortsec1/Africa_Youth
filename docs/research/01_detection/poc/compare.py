import json
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from analyze import analyze, time_of, POLICY, POLICY_START

ROOT = Path(__file__).resolve().parent


def run():
    cases = json.loads((ROOT / "comparison_cases.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "sample_events.json").read_text(encoding="utf-8"))
    base_file = next(e for e in sample if e["event_id"] == "evt-001")
    base_visit = next(e for e in sample if e["event_id"] == "evt-003")
    report = []
    for window in (30, 60, 300):
        methods = {name: {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
                   for name in ("time", "identity", "ordered")}
        details = []
        for case in cases:
            file, visit = deepcopy(base_file), deepcopy(base_visit)
            visit["occurred_at"] = (time_of(file) + timedelta(seconds=case["gap"])).isoformat()
            visit.update(device_id=case["device"], user_id=case["user"])
            visit["attributes"]["service_id"] = case["service"]
            candidate = (time_of(visit) >= POLICY_START and
                         POLICY.get(case["service"]) == "unapproved")
            near = candidate and abs(case["gap"]) <= window
            same = (file["device_id"] == visit["device_id"] and
                    bool(visit["user_id"]) and file["user_id"] == visit["user_id"])
            alerts = analyze([visit, file], window)["alerts"]
            predictions = {"time": near, "identity": near and same,
                           "ordered": any(a["rule_id"] == "R02" for a in alerts)}
            details.append({"case": case["id"], "expected": case["related"],
                            "predictions": predictions,
                            "insufficient_context": any(a["rule_id"] == "R05" for a in alerts)})
            if case["related"] is None:
                continue  # 정답 미확인은 오탐·미탐 집계에서 제외
            for method, predicted in predictions.items():
                label = ("TP" if predicted else "FN") if case["related"] else ("FP" if predicted else "TN")
                methods[method][label] += 1
        report.append({"window_seconds": window, "scored_cases": 8,
                       "excluded_cases": ["C09"], "counts": methods, "details": details})
    return {"synthetic": True, "policy_version": "demo-v1", "results": report}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
