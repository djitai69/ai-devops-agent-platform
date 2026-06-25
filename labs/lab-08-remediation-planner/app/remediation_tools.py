from typing import Dict, List


def detect_remediation_request(question: str) -> bool:
    q = question.lower()

    remediation_terms = [
        "fix",
        "remediate",
        "remediation",
        "repair",
        "resolve",
        "generate commands",
        "what commands",
        "how do i fix",
        "plan",
    ]

    return any(term in q for term in remediation_terms)


def build_kubernetes_secret_remediation(answer: str, sources: List[str]) -> str:
    return "\n".join(
        [
            "# Remediation Plan",
            "",
            "## Incident",
            "",
            "payment-service is blocked by a Kubernetes container configuration error.",
            "",
            "## Root Cause",
            "",
            'The workload expects Secret "payment-db-secret" with key "password". Kubernetes evidence shows the Secret or required key was unavailable when the pod was created.',
            "",
            "## Safety",
            "",
            "Mode: Human-in-the-loop",
            "Execution: Not automatic",
            "Risk: Medium",
            "",
            "Reason: updating Secrets can affect application startup and database connectivity.",
            "",
            "## Preconditions",
            "",
            "- Confirm the active Kubernetes context is correct.",
            "- Confirm namespace ai-sre-demo exists.",
            "- Confirm payment-service deployment exists.",
            '- Confirm the expected Secret name is "payment-db-secret".',
            '- Confirm the expected key is "password".',
            "- Use a real secret value from a secure source.",
            "- Do not paste real secrets into Git, logs, Slack, or tickets.",
            "",
            "## Step 1 — Inspect Current State",
            "",
            "```bash",
            "kubectl config current-context",
            "kubectl get ns ai-sre-demo",
            "kubectl get deployment payment-service -n ai-sre-demo",
            "kubectl get secret payment-db-secret -n ai-sre-demo",
            "kubectl get pods -n ai-sre-demo",
            "kubectl get events -n ai-sre-demo --sort-by=.lastTimestamp",
            "```",
            "",
            "## Step 2 — Apply Remediation",
            "",
            "If the Secret does not exist:",
            "",
            "```bash",
            "kubectl create secret generic payment-db-secret \\",
            "  --from-literal=password='<REPLACE_WITH_REAL_PASSWORD>' \\",
            "  -n ai-sre-demo",
            "```",
            "",
            "If the Secret exists but the key is wrong, update it safely:",
            "",
            "```bash",
            "kubectl create secret generic payment-db-secret \\",
            "  --from-literal=password='<REPLACE_WITH_REAL_PASSWORD>' \\",
            "  -n ai-sre-demo \\",
            "  --dry-run=client -o yaml | kubectl apply -f -",
            "```",
            "",
            "## Step 3 — Restart Workload",
            "",
            "```bash",
            "kubectl rollout restart deployment/payment-service -n ai-sre-demo",
            "kubectl rollout status deployment/payment-service -n ai-sre-demo",
            "```",
            "",
            "## Step 4 — Validate",
            "",
            "```bash",
            "kubectl get secret payment-db-secret -n ai-sre-demo",
            "kubectl get secret payment-db-secret -n ai-sre-demo -o jsonpath='{.data.password}' | wc -c",
            "kubectl get pods -n ai-sre-demo",
            "kubectl describe pod -n ai-sre-demo -l app=payment-service",
            "kubectl get events -n ai-sre-demo --sort-by=.lastTimestamp",
            "```",
            "",
            "Expected result:",
            "",
            "- payment-service pod reaches Running.",
            "- CreateContainerConfigError is gone.",
            "- Events no longer show missing Secret or missing key errors.",
            "",
            "## Rollback",
            "",
            "If the new Secret value is incorrect, restore the previous Secret from the approved source of truth.",
            "",
            "For this demo environment only:",
            "",
            "```bash",
            "kubectl delete secret payment-db-secret -n ai-sre-demo",
            "```",
            "",
            "Then recreate it with the correct value.",
            "",
            "## Human Approval Required",
            "",
            "Yes. This plan generates commands only. It does not execute changes automatically.",
        ]
    )



def build_generic_remediation(answer: str, sources: List[str]) -> str:
    source_lines = "\n".join([f"- {source}" for source in sources])

    return "\n".join(
        [
            "# Remediation Plan",
            "",
            "## 1. Summary",
            "",
            "A technical finding was detected and requires a human-reviewed remediation plan.",
            "",
            "## 2. Proposed Change",
            "",
            "Review the technical finding and apply the smallest safe change that addresses the root cause.",
            "",
            "## 3. Commands or Manifest",
            "",
            "No deterministic command template is available for this incident type yet.",
            "",
            "## 4. Risk Level",
            "",
            "Medium.",
            "",
            "## 5. Preconditions",
            "",
            "- Confirm the affected service and namespace.",
            "- Confirm the evidence is current.",
            "- Confirm the owner approves the change.",
            "- Avoid applying production changes automatically.",
            "",
            "## 6. Validation Steps",
            "",
            "- Re-run the original check.",
            "- Review logs, metrics, Kubernetes events, or relevant system status.",
            "- Confirm the incident condition is resolved.",
            "- Monitor for regressions.",
            "",
            "## 7. Rollback Plan",
            "",
            "Rollback should restore the previous known-good configuration.",
            "",
            "## 8. Human Approval Required",
            "",
            "Yes.",
            "",
            "## Evidence Sources",
            "",
            source_lines,
            "",
            "## Original Technical Finding",
            "",
            answer,
        ]
    )


def format_remediation_plan(
    question: str,
    incident_type: str,
    answer: str,
    sources: List[str],
) -> Dict[str, object]:
    text = answer.lower()

    if incident_type == "kubernetes" and "payment-db-secret" in text and "password" in text:
        plan = build_kubernetes_secret_remediation(answer, sources)
    else:
        plan = build_generic_remediation(answer, sources)

    return {
        "plan": plan,
        "sources": sources,
    }


def build_pre_remediation_diagnosis(
    incident_type: str,
    sources: List[str],
    k8s_context: str = "",
    runbook_context: str = "",
) -> str:
    """
    Build a short deterministic diagnosis for remediation planning.

    This avoids using the LLM for safety-critical remediation commands,
    while keeping graph.py generic.
    """

    combined_context = f"{k8s_context}\n{runbook_context}".lower()
    source_text = "\n".join(sources).lower()

    if (
        incident_type == "kubernetes"
        and (
            "payment-db-secret" in combined_context
            or "payment-db-secret" in source_text
            or "secret" in combined_context
        )
        and (
            "password" in combined_context
            or "key" in combined_context
            or "secret" in combined_context
        )
    ):
        return "\n".join(
            [
                "### Incident Summary",
                "A Kubernetes workload is blocked because the container configuration cannot be created.",
                "",
                "### Evidence",
                'The Kubernetes evidence indicates a missing or invalid Secret reference. The workload expects Secret "payment-db-secret" with key "password".',
                "",
                "### Probable Root Cause",
                'Secret "payment-db-secret" is missing or does not contain the required key "password".',
                "",
                "### Recommended Fix",
                'Create or correct Secret "payment-db-secret" with key "password", then restart the affected deployment if it exists.',
            ]
        )

    return "\n".join(
        [
            "### Incident Summary",
            "A remediation request was received for an infrastructure incident.",
            "",
            "### Probable Root Cause",
            "The exact root cause should be confirmed from the available evidence before applying changes.",
            "",
            "### Recommended Fix",
            "Generate a human-reviewed remediation plan with validation and rollback steps.",
        ]
    )

