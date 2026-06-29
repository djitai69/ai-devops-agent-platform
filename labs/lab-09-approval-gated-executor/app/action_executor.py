import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


AUDIT_LOG_PATH = Path("/app/data/action_audit_log.jsonl")


ALLOWED_NAMESPACES = {
    "ai-sre-demo",
}


ALLOWED_ACTIONS = {
    "get_pods",
    "get_events",
    "get_secret_metadata",
    "rollout_status",
    "restart_deployment",
    "create_demo_secret",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit_log(entry: Dict[str, object]) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def validate_namespace(namespace: str) -> None:
    if namespace not in ALLOWED_NAMESPACES:
        raise ValueError(
            f"Namespace '{namespace}' is not allowed. Allowed namespaces: {sorted(ALLOWED_NAMESPACES)}"
        )


def validate_action(action: str) -> None:
    if action not in ALLOWED_ACTIONS:
        raise ValueError(
            f"Action '{action}' is not allowed. Allowed actions: {sorted(ALLOWED_ACTIONS)}"
        )


def build_command(
    action: str,
    namespace: str,
    deployment: Optional[str] = None,
    secret_name: Optional[str] = None,
    secret_key: Optional[str] = None,
    secret_value: Optional[str] = None,
) -> List[str]:
    validate_action(action)
    validate_namespace(namespace)

    if action == "get_pods":
        return ["kubectl", "get", "pods", "-n", namespace]

    if action == "get_events":
        return ["kubectl", "get", "events", "-n", namespace, "--sort-by=.lastTimestamp"]

    if action == "get_secret_metadata":
        if not secret_name:
            raise ValueError("secret_name is required for get_secret_metadata")

        return ["kubectl", "get", "secret", secret_name, "-n", namespace]

    if action == "rollout_status":
        if not deployment:
            raise ValueError("deployment is required for rollout_status")

        return ["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace]

    if action == "restart_deployment":
        if not deployment:
            raise ValueError("deployment is required for restart_deployment")

        return ["kubectl", "rollout", "restart", f"deployment/{deployment}", "-n", namespace]

    if action == "create_demo_secret":
        if not secret_name:
            raise ValueError("secret_name is required for create_demo_secret")
        if not secret_key:
            raise ValueError("secret_key is required for create_demo_secret")
        if secret_value is None:
            raise ValueError("secret_value is required for create_demo_secret")

        return [
            "kubectl",
            "create",
            "secret",
            "generic",
            secret_name,
            f"--from-literal={secret_key}={secret_value}",
            "-n",
            namespace,
            "--dry-run=client",
            "-o",
            "yaml",
        ]

    raise ValueError(f"Unsupported action: {action}")


def preview_action(
    action: str,
    namespace: str,
    deployment: Optional[str] = None,
    secret_name: Optional[str] = None,
    secret_key: Optional[str] = None,
    secret_value: Optional[str] = None,
) -> Dict[str, object]:
    command = build_command(
        action=action,
        namespace=namespace,
        deployment=deployment,
        secret_name=secret_name,
        secret_key=secret_key,
        secret_value=secret_value,
    )

    redacted_command = redact_command(command)

    return {
        "action": action,
        "namespace": namespace,
        "approved": False,
        "will_execute": False,
        "command": redacted_command,
        "risk": classify_risk(action),
        "message": "Preview only. No command was executed.",
    }


def classify_risk(action: str) -> str:
    if action in {"get_pods", "get_events", "get_secret_metadata", "rollout_status"}:
        return "low"

    if action in {"restart_deployment", "create_demo_secret"}:
        return "medium"

    return "high"


def redact_command(command: List[str]) -> List[str]:
    redacted = []

    for part in command:
        if part.startswith("--from-literal="):
            key = part.split("=", 1)[0]
            redacted.append(f"{key}=<REDACTED>")
        else:
            redacted.append(part)

    return redacted


def execute_action(
    action: str,
    namespace: str,
    approved: bool,
    deployment: Optional[str] = None,
    secret_name: Optional[str] = None,
    secret_key: Optional[str] = None,
    secret_value: Optional[str] = None,
) -> Dict[str, object]:
    command = build_command(
        action=action,
        namespace=namespace,
        deployment=deployment,
        secret_name=secret_name,
        secret_key=secret_key,
        secret_value=secret_value,
    )

    redacted_command = redact_command(command)
    risk = classify_risk(action)

    if not approved:
        result = {
            "timestamp": now_iso(),
            "action": action,
            "namespace": namespace,
            "approved": False,
            "executed": False,
            "risk": risk,
            "command": redacted_command,
            "stdout": "",
            "stderr": "Action was not approved. No command was executed.",
            "returncode": None,
        }

        audit_log(result)
        return result

    if action == "create_demo_secret":
        # Use safe apply pattern for idempotent Secret creation/update.
        create_result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        if create_result.returncode != 0:
            result = {
                "timestamp": now_iso(),
                "action": action,
                "namespace": namespace,
                "approved": approved,
                "executed": True,
                "risk": risk,
                "command": redacted_command,
                "stdout": create_result.stdout,
                "stderr": create_result.stderr,
                "returncode": create_result.returncode,
            }
            audit_log(result)
            return result

        apply_result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=create_result.stdout,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        result = {
            "timestamp": now_iso(),
            "action": action,
            "namespace": namespace,
            "approved": approved,
            "executed": True,
            "risk": risk,
            "command": redacted_command + ["|", "kubectl", "apply", "-f", "-"],
            "stdout": apply_result.stdout,
            "stderr": apply_result.stderr,
            "returncode": apply_result.returncode,
        }

        audit_log(result)
        return result

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    result = {
        "timestamp": now_iso(),
        "action": action,
        "namespace": namespace,
        "approved": approved,
        "executed": True,
        "risk": risk,
        "command": redacted_command,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }

    audit_log(result)
    return result


def read_action_history(limit: int = 20) -> Dict[str, object]:
    if not AUDIT_LOG_PATH.exists():
        return {
            "actions": [],
        }

    lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    recent_lines = lines[-limit:]

    actions = [json.loads(line) for line in recent_lines if line.strip()]

    return {
        "actions": actions,
    }
