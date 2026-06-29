import os
import re
from pathlib import Path
from typing import List, Dict, Optional


K8S_DIR = Path(os.getenv("K8S_DIR", "/data/k8s"))


IMPORTANT_TERMS = [
    "error",
    "failed",
    "warning",
    "createcontainerconfigerror",
    "crashloopbackoff",
    "imagepullbackoff",
    "secret",
    "configmap",
    "pending",
    "not found",
    "db_password",
]


def list_k8s_files() -> List[str]:
    if not K8S_DIR.exists():
        return []

    return sorted([p.name for p in K8S_DIR.glob("*.txt")])


def read_k8s_file(filename: str) -> str:
    file_path = K8S_DIR / filename

    if not file_path.exists():
        return ""

    return file_path.read_text(encoding="utf-8")


def get_all_k8s_text() -> str:
    return "\n".join(read_k8s_file(filename) for filename in list_k8s_files())


def search_k8s_evidence(question: str, limit: int = 80) -> List[Dict[str, str]]:
    q = question.lower()
    results = []

    for filename in list_k8s_files():
        text = read_k8s_file(filename)

        for line in text.splitlines():
            line_lower = line.lower()

            question_match = any(
                token in line_lower
                for token in q.replace("?", "").split()
                if len(token) >= 4
            )

            important_match = any(term in line_lower for term in IMPORTANT_TERMS)

            if question_match or important_match:
                results.append(
                    {
                        "source": filename,
                        "line": line,
                    }
                )

            if len(results) >= limit:
                return results

    return results


def extract_first(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def parse_k8s_diagnosis() -> Dict[str, object]:
    """
    Parse Kubernetes snapshots into a structured diagnosis.

    This is the source of truth for Kubernetes startup/configuration incidents.
    The LLM should format this diagnosis, not invent the root cause.
    """

    text = get_all_k8s_text()

    pod_name = extract_first(r"Name:\s+([^\s]+)", text)
    namespace = extract_first(r"Namespace:\s+([^\s]+)", text)
    pod_status = extract_first(r"Status:\s+([^\s]+)", text)
    container_reason = extract_first(r"Reason:\s+([A-Za-z0-9]+)", text)

    env_var = None
    secret_key = None
    secret_name = None

    env_match = re.search(
        r"([A-Z0-9_]+):\s+<set to the key '([^']+)' in secret '([^']+)'",
        text,
        re.IGNORECASE,
    )

    if env_match:
        env_var = env_match.group(1)
        secret_key = env_match.group(2)
        secret_name = env_match.group(3)

    missing_secret = extract_first(r'secret "([^"]+)" not found', text)

    if missing_secret:
        secret_name = missing_secret

    missing_key = extract_first(r"couldn't find key ([^\s]+) in Secret", text)

    if missing_key:
        secret_key = missing_key

    event_messages = []

    for line in text.splitlines():
        line_lower = line.lower()
        if "secret" in line_lower or "failed" in line_lower or "error" in line_lower:
            event_messages.append(line.strip())

    diagnosis_type = "unknown"
    root_cause = "Unable to determine root cause from Kubernetes evidence."
    recommended_fix = "Collect more Kubernetes evidence with kubectl describe pod and kubectl get events."
    validation_commands = []

    if container_reason == "CreateContainerConfigError" and secret_name:
        diagnosis_type = "missing_secret_or_secret_key"

        if secret_key:
            root_cause = (
                f'Kubernetes cannot create the container because Secret "{secret_name}" '
                f'is missing or does not contain the required key "{secret_key}".'
            )
            recommended_fix = (
                f'Create Secret "{secret_name}" with key "{secret_key}", '
                f'or update the deployment to reference the correct Secret/key.'
            )
        else:
            root_cause = (
                f'Kubernetes cannot create the container because Secret "{secret_name}" is missing.'
            )
            recommended_fix = (
                f'Create Secret "{secret_name}", or update the deployment to reference the correct Secret.'
            )

        ns = namespace or "<namespace>"
        pod = pod_name or "<pod-name>"

        validation_commands = [
            f"kubectl get secret {secret_name} -n {ns}",
            f"kubectl describe pod {pod} -n {ns}",
            f"kubectl get events -n {ns} --sort-by=.lastTimestamp",
            f"kubectl get pods -n {ns}",
        ]

    elif container_reason == "ImagePullBackOff":
        diagnosis_type = "image_pull_error"
        root_cause = "Kubernetes cannot pull the container image."
        recommended_fix = "Verify image name, tag, registry access, and imagePullSecrets."

    elif container_reason == "CrashLoopBackOff":
        diagnosis_type = "application_crash"
        root_cause = "The container starts but exits repeatedly."
        recommended_fix = "Inspect container logs, previous logs, exit code, probes, and application configuration."

    return {
        "diagnosis_type": diagnosis_type,
        "pod_name": pod_name,
        "namespace": namespace,
        "pod_status": pod_status,
        "container_reason": container_reason,
        "env_var": env_var,
        "secret_name": secret_name,
        "secret_key": secret_key,
        "event_messages": event_messages[:8],
        "root_cause": root_cause,
        "recommended_fix": recommended_fix,
        "validation_commands": validation_commands,
    }


def format_k8s_evidence(question: str) -> Dict[str, object]:
    evidence = search_k8s_evidence(question)
    diagnosis = parse_k8s_diagnosis()

    sources = sorted(set(item["source"] for item in evidence))

    raw_evidence = "\n".join(
        [f"Source: {item['source']}\n{item['line']}" for item in evidence]
    )

    structured_context = "\n".join(
        [
            "Structured Kubernetes Diagnosis:",
            f"- Diagnosis type: {diagnosis['diagnosis_type']}",
            f"- Pod name: {diagnosis['pod_name']}",
            f"- Namespace: {diagnosis['namespace']}",
            f"- Pod status: {diagnosis['pod_status']}",
            f"- Container reason: {diagnosis['container_reason']}",
            f"- Environment variable: {diagnosis['env_var']}",
            f"- Secret name: {diagnosis['secret_name']}",
            f"- Secret key: {diagnosis['secret_key']}",
            f"- Root cause: {diagnosis['root_cause']}",
            f"- Recommended fix: {diagnosis['recommended_fix']}",
            "- Validation commands:",
            *[f"  - {cmd}" for cmd in diagnosis["validation_commands"]],
            "- Event messages:",
            *[f"  - {msg}" for msg in diagnosis["event_messages"]],
            "",
            "Raw Kubernetes Evidence:",
            raw_evidence,
        ]
    )

    return {
        "sources": sources,
        "context": structured_context,
        "diagnosis": diagnosis,
    }
