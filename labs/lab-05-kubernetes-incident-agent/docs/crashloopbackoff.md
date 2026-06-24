# Kubernetes CrashLoopBackOff Runbook

## Symptoms

A pod is repeatedly starting and crashing. Kubernetes reports the pod status as CrashLoopBackOff.

## Common Causes

- Application process exits immediately
- Missing environment variable
- Missing Kubernetes Secret or ConfigMap
- Invalid container command or arguments
- Application cannot connect to database
- Failed health check
- Insufficient memory causing OOMKilled

## Investigation Steps

1. Check pod status:

kubectl get pods -n <namespace>

2. Describe the pod:

kubectl describe pod <pod-name> -n <namespace>

3. Check logs:

kubectl logs <pod-name> -n <namespace>

4. Check previous logs:

kubectl logs <pod-name> -n <namespace> --previous

5. Check events:

kubectl get events -n <namespace> --sort-by=.lastTimestamp

## Recommended Fixes

- If a secret is missing, create or correct the secret reference.
- If the app exits due to config error, fix the environment variables.
- If the pod is OOMKilled, increase memory limit or reduce memory usage.
- If the health check is too aggressive, adjust readiness and liveness probes.
