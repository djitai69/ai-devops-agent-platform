# Remediation Planning Runbook

## Goal

Generate safe, reviewable remediation plans for infrastructure incidents.

## Principles

- Do not apply production changes automatically.
- Prefer human approval before changes.
- Include exact commands or manifests when possible.
- Include validation commands.
- Include rollback plan.
- Include risk level.
- Identify whether the change is low, medium, or high risk.

## Required Remediation Plan Structure

1. Summary
2. Proposed Change
3. Commands or Manifest
4. Risk Level
5. Preconditions
6. Validation Steps
7. Rollback Plan
8. Human Approval Required

## Kubernetes Missing Secret Example

If a pod is blocked by CreateContainerConfigError because a Secret is missing:

Proposed change:
Create the missing Secret with the required key.

Command:
kubectl create secret generic <secret-name> \
  --from-literal=<key>='<value>' \
  -n <namespace>

Validation:
kubectl get secret <secret-name> -n <namespace>
kubectl rollout restart deployment/<deployment-name> -n <namespace>
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>

Rollback:
kubectl delete secret <secret-name> -n <namespace>

Risk:
Medium if production. Low if demo/dev namespace.

Approval:
Required before applying.
