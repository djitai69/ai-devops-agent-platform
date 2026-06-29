# Kubernetes FinOps Rightsizing Runbook

## Goal

Reduce Kubernetes cloud cost without causing performance or reliability issues.

## Common Waste Patterns

- CPU requests much higher than actual usage
- Memory requests much higher than actual usage
- Idle workloads running continuously
- Unused persistent volumes
- Old snapshots
- Load balancers no longer receiving traffic
- Overprovisioned nodes

## Rightsizing Guidance

CPU request recommendation:
- Use average CPU and p95 CPU.
- Recommended CPU request should usually be above p95 usage.
- Avoid reducing CPU too aggressively.
- Monitor for at least 7 days after changes.

Memory request recommendation:
- Use p95 memory as the main guide.
- Keep a safety buffer because memory pressure can cause OOMKilled.
- Do not reduce memory below p95 usage.

Idle resource cleanup:
- Validate ownership.
- Confirm no active traffic or dependency.
- Take backup when needed.
- Delete only after review.

## Safety Rules

- Do not apply changes automatically.
- Generate recommendations for human review.
- Roll out changes gradually.
- Monitor latency, errors, restarts, and saturation after rightsizing.

## RCA / Recommendation Template

Finding:
Recommended change:
Estimated monthly savings:
Risk:
Validation:
Rollback plan:
