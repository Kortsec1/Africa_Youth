from pathlib import Path

import pytest

from proxy.policy import PolicyError, load_policy


def write_policy(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_load_policy_and_decide(tmp_path):
    policy = load_policy(
        write_policy(
            tmp_path / "policy.yaml",
            """
default_action: block
upstream:
  host: 127.0.0.1
  port: 8443
rules:
  - sni: allowed.test
    action: allow
    reason: allowed
""",
        )
    )
    assert policy.decide("allowed.test").action == "allow"
    assert policy.decide("unknown.test").action == "block"
    assert policy.decide(None).action == "block"


def test_missing_policy_file():
    with pytest.raises(PolicyError):
        load_policy("/missing/policy.yaml")


def test_invalid_action_rejected(tmp_path):
    with pytest.raises(PolicyError, match="invalid action"):
        load_policy(
            write_policy(
                tmp_path / "policy.yaml",
                """
default_action: block
upstream:
  host: 127.0.0.1
  port: 8443
rules:
  - sni: allowed.test
    action: pass
""",
            )
        )


def test_duplicate_sni_rejected(tmp_path):
    with pytest.raises(PolicyError, match="duplicate"):
        load_policy(
            write_policy(
                tmp_path / "policy.yaml",
                """
default_action: block
upstream:
  host: 127.0.0.1
  port: 8443
rules:
  - sni: allowed.test
    action: allow
  - sni: allowed.test
    action: block
""",
            )
        )


def test_external_upstream_rejected(tmp_path):
    with pytest.raises(PolicyError, match="loopback|local"):
        load_policy(
            write_policy(
                tmp_path / "policy.yaml",
                """
default_action: block
upstream:
  host: 8.8.8.8
  port: 443
rules: []
""",
            )
        )
