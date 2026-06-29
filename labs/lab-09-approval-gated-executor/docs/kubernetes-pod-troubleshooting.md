# Kubernetes Pod Troubleshooting Runbook

## Common Pod Failure States

### CrashLoopBackOff

The container starts but repeatedly crashes.

Common causes:

- application exits immediately
- missing environment variable
- failing health check
- OOMKilled
- application dependency unavailable

### ImagePullBackOff

Kubernetes cannot pull the container image.

Common causes:

- wrong image name
- wrong image tag
- private registry credentials missing
- registry unavailable

### CreateContainerConfigError

Kubernetes cannot create the container configuration.

Common causes:

- referenced Secret does not exist
- referenced ConfigMap does not exist
- secret key is missing
- invalid environment variable reference
- invalid volume mount reference

## Investigation Steps

1. Check pods:

kubectl get pods -n <namespace>

2. Describe the failing pod:

kubectl describe pod <pod-name> -n <namespace>

3. Check events:

kubectl get events -n <namespace> --sort-by=.lastTimestamp

4. Check logs if the container started:

kubectl logs <pod-name> -n <namespace>

5. Check previous logs if the container restarted:

kubectl logs <pod-name> -n <namespace> --previous

## Recommended Fixes

If the error is CreateContainerConfigError and the event says a Secret is missing, create the missing Secret or update the deployment to reference the correct Secret.

If the error says a key is missing inside a Secret, add the missing key or update the environment variable reference.

## RCA Template

The pod failed to start because Kubernetes could not create the container configuration. Evidence should include pod status, describe output, and Kubernetes events.
