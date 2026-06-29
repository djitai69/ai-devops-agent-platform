import os
import requests
from typing import Dict, List


def send_to_slack(message: str) -> Dict[str, object]:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        return {
            "sent": False,
            "reason": "SLACK_WEBHOOK_URL is not configured.",
        }

    response = requests.post(
        webhook_url,
        json={"text": message},
        timeout=10,
    )

    response.raise_for_status()

    return {
        "sent": True,
        "status_code": response.status_code,
    }


def detect_report_type(question: str) -> str:
    q = question.lower()

    if "slack" in q or "chatops" in q or "update" in q or "message" in q:
        return "chatops"

    return "unknown"


def clean_line(line: str) -> str:
    return (
        line.strip()
        .replace("###", "")
        .replace("**", "")
        .replace("`", "")
        .strip()
    )


def extract_section(answer: str, section_names: List[str], max_lines: int = 4) -> str:
    """
    Extract a short section from a markdown-ish RCA answer.
    This is generic and does not depend on a specific incident.
    """

    lines = answer.splitlines()
    normalized = [line.lower().strip().replace(":", "") for line in lines]

    start_index = None

    for i, line in enumerate(normalized):
        for section in section_names:
            if section.lower() in line:
                start_index = i + 1
                break

        if start_index is not None:
            break

    if start_index is None:
        return ""

    collected = []

    for line in lines[start_index:]:
        stripped = clean_line(line)

        if not stripped:
            continue

        lower = stripped.lower()

        # Stop if we hit the next section heading.
        if any(
            heading in lower
            for heading in [
                "incident summary",
                "cost summary",
                "evidence",
                "probable root cause",
                "recommended fix",
                "recommended actions",
                "validation commands",
                "validation plan",
                "suggested next check",
                "risk and safety notes",
                "conclusion",
            ]
        ):
            break

        collected.append(stripped)

        if len(collected) >= max_lines:
            break

    return "\n".join(collected)


def first_non_empty_summary(answer: str) -> str:
    """
    Fallback summary if section extraction fails.
    """

    for line in answer.splitlines():
        stripped = clean_line(line)

        if not stripped:
            continue

        lower = stripped.lower()

        if lower.startswith("answer"):
            continue

        if lower in [
            "incident summary",
            "cost summary",
            "evidence",
            "probable root cause",
            "recommended fix",
            "recommended actions",
        ]:
            continue

        return stripped

    return "The agent produced a technical recommendation that requires review."


def summarize_sources(sources: List[str]) -> str:
    source_types = []

    if any(source.startswith("k8s:") for source in sources):
        source_types.append("Kubernetes evidence")
    if any(source.startswith("finops:") for source in sources):
        source_types.append("FinOps cost/utilization data")
    if any(source.startswith("log:") for source in sources):
        source_types.append("application logs")
    if any(source.startswith("metrics:") for source in sources):
        source_types.append("service metrics")
    if any(source.startswith("runbook:") for source in sources):
        source_types.append("runbook guidance")

    if not source_types:
        source_types.append("agent evidence")

    return "\n".join([f"- {item}" for item in source_types])


def extract_action_items(answer: str, max_items: int = 4) -> List[str]:
    """
    Extract action-like lines from the existing answer.
    Generic across Kubernetes, FinOps, logs, metrics, etc.
    """

    action_section = extract_section(
        answer,
        ["Recommended Fix", "Recommended Actions", "Next Actions", "Suggested Next Check"],
        max_lines=8,
    )

    candidates = []

    for line in action_section.splitlines():
        stripped = clean_line(line)

        if not stripped:
            continue

        # Remove common list prefixes.
        stripped = stripped.lstrip("-").strip()
        stripped = stripped.lstrip("0123456789.").strip()

        if stripped:
            candidates.append(stripped)

    if not candidates:
        candidates = [
            "Review the technical recommendation with the responsible engineer.",
            "Validate the evidence before making changes.",
            "Apply changes gradually where relevant.",
            "Monitor impact after the change.",
        ]

    return candidates[:max_items]


def format_chatops_update(
    question: str,
    incident_type: str,
    answer: str,
    sources: List[str],
) -> Dict[str, object]:
    summary = extract_section(
        answer,
        ["Incident Summary", "Cost Summary", "Summary"],
        max_lines=3,
    )

    if not summary:
        summary = first_non_empty_summary(answer)

    root_cause = extract_section(
        answer,
        ["Probable Root Cause", "Root Cause"],
        max_lines=3,
    )

    actions = extract_action_items(answer)
    action_lines = "\n".join([f"- {action}" for action in actions])

    evidence_summary = summarize_sources(sources)
    source_lines = "\n".join([f"- {source}" for source in sources])

    status = "Investigating / Action Recommended"

    if incident_type == "finops":
        status = "Action Recommended"

    root_cause_block = ""

    if root_cause:
        root_cause_block = f"""
Likely Cause:
{root_cause}
"""

    message = f"""🚨 Ops Update

Status:
{status}

Summary:
{summary}
{root_cause_block}
Evidence Used:
{evidence_summary}

Next Actions:
{action_lines}

Owner:
Platform / SRE team

Next Update:
After validation or once mitigation is applied.

Sources:
{source_lines}
"""

    return {
        "message": message,
        "sources": sources,
    }
