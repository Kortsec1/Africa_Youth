import json
import sys
from datetime import datetime, timedelta

# 실험용 정책. 실제 조직의 정책이 아니다.
POLICY = {"AI-DEMO": "unapproved", "AI-OK": "approved"}
POLICY_VERSION = "demo-v1"
POLICY_START = datetime.fromisoformat("2026-11-01T00:00:00+00:00")
RULES = {
    "R01": ("policy_review", "단일 기록", "미승인 서비스 방문 기록"),
    "R02": ("context_review", "상관 정황", "파일 읽기 후 미승인 서비스 방문"),
    "R03": ("policy_review", "상관 정황", "미승인 서비스 반복 방문"),
    "R04": ("insufficient_context", "판단 보류", "서비스 승인 정책 미확인"),
    "R05": ("insufficient_context", "판단 보류", "사용자 누락으로 행위 연결 불가"),
}


def time_of(event):
    value = datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
    if value.utcoffset() is None:
        raise ValueError("occurred_at에 시간대가 필요합니다.")
    return value


def analyze(events, window=60):
    if window <= 0:
        raise ValueError("시간 범위는 양수여야 합니다.")
    unique = {}
    for event in events:
        if event["synthetic"] is not True:
            raise ValueError("현재 버전은 가상 데이터 전용입니다.")
        if not event["device_id"]:
            raise ValueError("device_id가 필요합니다.")
        event_id = event["event_id"]
        if event_id in unique and unique[event_id] != event:
            raise ValueError("동일 event_id의 내용 충돌: " + event_id)
        unique[event_id] = event
    timeline = sorted(unique.values(), key=lambda e: (time_of(e), e["event_id"]))
    alerts = []

    def status(event):
        if time_of(event) < POLICY_START:
            return "unknown"
        return POLICY.get(event["attributes"].get("service_id"), "unknown")

    def emit(rule, evidence):
        category, level, description = RULES[rule]
        alerts.append({
            "rule_id": rule, "category": category, "assessment_level": level,
            "description": description,
            "evidence_ids": [e["event_id"] for e in evidence],
            "observed_facts": [e["attributes"] for e in evidence],
            "inference": "두 행위가 관련되었을 가능성" if rule == "R02" else None,
        })

    files = [e for e in timeline if e["event_type"] == "file_access"
             and e["attributes"].get("access_kind") == "read_data"]
    groups = {}
    for visit in timeline:
        if visit["event_type"] != "ai_service_access":
            continue
        if status(visit) == "unknown":
            emit("R04", [visit])
        if visit["attributes"].get("observation_kind") != "browser_visit":
            continue
        if status(visit) == "unapproved":
            emit("R01", [visit])
            if visit["user_id"]:
                key = (visit["device_id"], visit["user_id"],
                       visit["attributes"]["service_id"])
                groups.setdefault(key, []).append(visit)
        for file in files:
            gap = (time_of(visit) - time_of(file)).total_seconds()
            if file["device_id"] != visit["device_id"] or not 0 < gap <= window:
                continue
            if not file["user_id"] or not visit["user_id"]:
                emit("R05", [file, visit])
            elif file["user_id"] == visit["user_id"] and status(visit) == "unapproved":
                emit("R02", [file, visit])

    for visits in groups.values():
        clusters = []
        for visit in visits:
            end = time_of(visit)
            start = end - timedelta(seconds=window)
            matched = [e for e in visits if start <= time_of(e) <= end]
            if len(matched) < 3:
                continue
            hit = {"start": start.isoformat(), "end": end.isoformat(),
                   "evidence_ids": [e["event_id"] for e in matched]}
            if clusters and start <= clusters[-1]["end"]:
                clusters[-1]["end"] = end
                clusters[-1]["hits"].append(hit)
            else:
                clusters.append({"end": end, "hits": [hit]})
        for cluster in clusters:
            ids = {i for hit in cluster["hits"] for i in hit["evidence_ids"]}
            emit("R03", [e for e in visits if e["event_id"] in ids])
            alerts[-1]["matched_windows"] = cluster["hits"]
    return {
        "synthetic": True, "policy_version": POLICY_VERSION,
        "parameters": {"window_seconds": window, "repeat_count": 3},
        "limitation": "가상 데이터 결과이며 질문 전송·파일 업로드·유출을 입증하지 않습니다.",
        "timeline": [e["event_id"] for e in timeline],
        "events": timeline, "alerts": alerts,
    }


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as source:
        events = json.load(source)
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    print(json.dumps(analyze(events, window), ensure_ascii=False, indent=2))
