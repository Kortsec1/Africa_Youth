import unittest
from copy import deepcopy
from datetime import timedelta
from analyze import analyze, POLICY_START


def event(i, seconds, kind="visit", device="PC-A", user="USER-01", service="AI-DEMO"):
    return {
        "event_id": f"evt-{i}",
        "occurred_at": (POLICY_START + timedelta(seconds=seconds)).isoformat(),
        "device_id": device, "user_id": user, "process_entity_id": None,
        "event_type": "file_access" if kind == "file" else "ai_service_access",
        "source": "synthetic", "source_ref": f"synthetic:{i}", "synthetic": True,
        "attributes": {"access_kind": "read_data", "file_path": "C:\\Test\\sample.txt"}
        if kind == "file" else {"service_id": service, "domain": "ai.example.com",
                                "observation_kind": "browser_visit"},
    }


class TestAnalyze(unittest.TestCase):
    def test_scenarios(self):
        f = event(1, 0, "file")
        cases = [
            ([event(2, 40, service="AI-OK")], []),
            ([event(2, 40)], ["R01"]),
            ([f, event(2, 40)], ["R01", "R02"]),
            ([f, event(2, 40, device="PC-B")], ["R01"]),
            ([f, event(2, 40, user="USER-02")], ["R01"]),
            ([f, event(2, 61)], ["R01"]),
            ([event(1, 10, "file"), event(2, 0)], ["R01"]),
            ([event(1, 0), event(2, 20), event(3, 40)], ["R01"] * 3 + ["R03"]),
            ([event(1, 0), event(2, 20)], ["R01"] * 2),
            ([event(1, 0, service="UNKNOWN")], ["R04"]),
            ([f, event(2, 40, user=None)], ["R01", "R05"]),
            ([f, event(2, 60)], ["R01", "R02"]),
            ([f, event(2, 0)], ["R01"]),
        ]
        for number, (events, expected) in enumerate(cases, 1):
            with self.subTest(case=f"T{number:02}"):
                actual = [a["rule_id"] for a in analyze(events)["alerts"]]
                self.assertEqual(sorted(actual), sorted(expected))

    def test_order_and_duplicate(self):
        a, b = event(1, 0), event(2, 40)
        result = analyze([b, a, deepcopy(a)])
        self.assertEqual(result["timeline"], ["evt-1", "evt-2"])
        self.assertEqual(len(result["alerts"]), 2)

    def test_conflicting_id(self):
        with self.assertRaises(ValueError):
            analyze([event(1, 0), event(1, 10)])

    def test_missing_timezone(self):
        a = event(1, 0)
        a["occurred_at"] = "2026-11-15T10:00:00"
        with self.assertRaises(ValueError):
            analyze([a])

    def test_time_windows(self):
        data = [event(1, 0, "file"), event(2, 40)]
        for window, expected in [(30, False), (60, True), (300, True)]:
            self.assertEqual(any(a["rule_id"] == "R02" for a in
                                 analyze(data, window)["alerts"]), expected)

    def test_overlapping_repeats(self):
        data = [event(i, s) for i, s in enumerate([0, 20, 40, 60, 300, 320, 340])]
        alerts = [a for a in analyze(data)["alerts"] if a["rule_id"] == "R03"]
        self.assertEqual(len(alerts), 2)
        self.assertEqual(len(alerts[0]["matched_windows"]), 2)
        self.assertEqual(len(alerts[0]["evidence_ids"]), 4)

    def test_policy_and_missing_user(self):
        self.assertEqual(analyze([event(1, -1)])["alerts"][0]["rule_id"], "R04")
        data = [event(1, 0, "file", user=None), event(2, 40, user=None)]
        self.assertEqual([a["rule_id"] for a in analyze(data)["alerts"]], ["R01", "R05"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
