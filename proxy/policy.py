from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ipaddress

import yaml


VALID_ACTIONS = {"allow", "block"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "test-server"}


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    sni: str
    action: str
    reason: str


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str


@dataclass(frozen=True)
class Policy:
    default_action: str
    upstream_host: str
    upstream_port: int
    rules: dict[str, Rule]

    def decide(self, sni: str | None) -> Decision:
        if sni and sni.lower() in self.rules:
            rule = self.rules[sni.lower()]
            return Decision(rule.action, rule.reason)
        if sni is None:
            return Decision(self.default_action, "SNI 없음: 기본 정책 적용")
        return Decision(self.default_action, "알 수 없는 SNI: 기본 정책 적용")


def load_policy(path: str | Path) -> Policy:
    policy_path = Path(path)
    if not policy_path.exists():
        raise PolicyError(f"policy file not found: {policy_path}")
    try:
        raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PolicyError(f"invalid YAML policy: {exc}") from exc
    if not isinstance(raw, dict):
        raise PolicyError("policy root must be a mapping")

    default_action = raw.get("default_action")
    if default_action not in VALID_ACTIONS:
        raise PolicyError("default_action must be allow or block")

    upstream = raw.get("upstream")
    if not isinstance(upstream, dict):
        raise PolicyError("upstream must be a mapping")
    host = upstream.get("host")
    port = upstream.get("port")
    _validate_local_upstream(host, port)

    rules_raw = raw.get("rules", [])
    if not isinstance(rules_raw, list):
        raise PolicyError("rules must be a list")
    rules: dict[str, Rule] = {}
    for item in rules_raw:
        if not isinstance(item, dict):
            raise PolicyError("each rule must be a mapping")
        sni = item.get("sni")
        action = item.get("action")
        reason = item.get("reason", "")
        if not isinstance(sni, str) or not sni:
            raise PolicyError("rule.sni must be a non-empty string")
        key = sni.lower()
        if key in rules:
            raise PolicyError(f"duplicate rule for SNI: {sni}")
        if action not in VALID_ACTIONS:
            raise PolicyError(f"invalid action for {sni}: {action}")
        if not isinstance(reason, str):
            raise PolicyError(f"reason for {sni} must be a string")
        rules[key] = Rule(key, action, reason)

    return Policy(default_action, str(host), int(port), rules)


def _validate_local_upstream(host: object, port: object) -> None:
    if not isinstance(host, str) or not host:
        raise PolicyError("upstream.host must be a non-empty string")
    if host not in LOCAL_HOSTS:
        try:
            ip = ipaddress.ip_address(host)
        except ValueError as exc:
            raise PolicyError("upstream.host must be local only") from exc
        if not ip.is_loopback:
            raise PolicyError("upstream.host must be loopback")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise PolicyError("upstream.port must be an integer between 1 and 65535")
