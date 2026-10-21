import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


ATTESTATION_KEY = b"chapter-19-attestation-key"


def verify_attestation(
    attestation: dict[str, str],
    expected_issuer: str,
    expected_subject: str,
    key: bytes,
) -> bool:
    if attestation.get("issuer") != expected_issuer:
        return False
    if attestation.get("subject") != expected_subject:
        return False
    message = f"{expected_issuer}:{expected_subject}".encode()
    expected_signature = "hmac-sha256:" + hmac.new(
        key, message, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(
        attestation.get("signature", ""), expected_signature
    )


def check_manifest(deployment_path: Path) -> tuple[dict[str, Any], bool]:
    manifest = json.loads(deployment_path.read_text(encoding="utf-8"))
    required_fields = {
        "agent_version",
        "artifact_digest",
        "build_attestation",
        "dependency_lock_digest",
        "source_revision",
        "model",
        "model_digest",
        "prompt_version",
        "prompt_digest",
        "policy_version",
        "runtime_config_digest",
        "tool_schema_version",
        "evaluation_dataset",
        "evaluation_dataset_digest",
        "evaluation_attestation",
        "environment",
    }
    complete = required_fields.issubset(manifest)
    if not complete:
        return manifest, False

    digest_fields = {
        "artifact_digest",
        "dependency_lock_digest",
        "model_digest",
        "prompt_digest",
        "runtime_config_digest",
        "evaluation_dataset_digest",
    }
    def is_sha256_digest(value: Any) -> bool:
        if not isinstance(value, str) or not value.startswith("sha256:"):
            return False
        hexadecimal = value.removeprefix("sha256:")
        return len(hexadecimal) == 64 and all(
            character in "0123456789abcdef" for character in hexadecimal
        )

    digests_valid = all(is_sha256_digest(manifest[field]) for field in digest_fields)
    build_verified = verify_attestation(
        manifest["build_attestation"],
        expected_issuer="chapter-ci",
        expected_subject=manifest["artifact_digest"],
        key=ATTESTATION_KEY,
    )
    evaluation_subject = (
        f'{manifest["artifact_digest"]}:{manifest["evaluation_dataset_digest"]}'
    )
    evaluation_verified = verify_attestation(
        manifest["evaluation_attestation"],
        expected_issuer="chapter-evaluator",
        expected_subject=evaluation_subject,
        key=ATTESTATION_KEY,
    )
    return manifest, digests_valid and build_verified and evaluation_verified


def fingerprint_arguments(arguments: dict[str, Any], key: bytes, scope: str) -> str:
    canonical_arguments = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    message = f"{scope}:{canonical_arguments}".encode()
    digest = hmac.new(key, message, hashlib.sha256).hexdigest()
    return f"hmac-sha256:{digest}"


def check_telemetry(event: dict[str, Any]) -> bool:
    sensitive_keys = {
        "arguments",
        "authorization",
        "identity",
        "password",
        "prompt",
        "secret",
        "token",
    }

    def is_safe(value: Any) -> bool:
        if isinstance(value, dict):
            return all(
                key.lower() not in sensitive_keys and is_safe(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return all(is_safe(child) for child in value)
        if isinstance(value, str):
            lowered = value.lower()
            return not lowered.startswith(("bearer ", "sk-"))
        return True

    return is_safe(event)


def apply_budget(model_steps: int, maximum_steps: int) -> str:
    return "max_steps" if model_steps > maximum_steps else "continue"


def main() -> None:
    deployment_path = Path(__file__).resolve().parents[1] / "deployment.json"
    manifest, manifest_verified = check_manifest(deployment_path)
    fingerprint = fingerprint_arguments(
        {"destination": "Springfield"},
        key=b"local-exercise-key",
        scope="travel-agent:2026-08-03",
    )
    safe_event = {
        "event_type": "tool_requested",
        "run_id": "run-review",
        "versions": {
            "agent": manifest["agent_version"],
            "model": manifest["model"],
            "policy": manifest["policy_version"],
        },
        "tool": {"name": "search_flights", "arguments_fingerprint": fingerprint},
    }
    unsafe_event = {
        "event_type": "tool_requested",
        "details": {"arguments": {"flight": "FL-204"}},
    }
    telemetry_safe = check_telemetry(safe_event)
    unsafe_telemetry_rejected = not check_telemetry(unsafe_event)
    candidate_budget_decision = apply_budget(model_steps=3, maximum_steps=4)
    over_budget_decision = apply_budget(model_steps=5, maximum_steps=4)
    increase_traffic = (
        manifest_verified
        and telemetry_safe
        and unsafe_telemetry_rejected
        and candidate_budget_decision == "continue"
    )

    assert manifest_verified is True
    assert telemetry_safe is True
    assert unsafe_telemetry_rejected is True
    assert candidate_budget_decision == "continue"
    assert over_budget_decision == "max_steps"
    assert increase_traffic is True

    print(f"Manifest verified: {manifest_verified}")
    print(f"Telemetry safe: {telemetry_safe}")
    print(f"Unsafe telemetry rejected: {unsafe_telemetry_rejected}")
    print(f"Candidate budget decision: {candidate_budget_decision}")
    print(f"Over-budget example decision: {over_budget_decision}")
    print(f"Increase traffic: {increase_traffic}")


if __name__ == "__main__":
    main()
