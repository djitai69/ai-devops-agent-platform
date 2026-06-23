# Kubernetes HPA Scaling Runbook

## Symptoms

The application is slow or overloaded, but Kubernetes is not adding more pods.

## Common Causes

- HPA maxReplicas already reached
- CPU request is missing
- Metrics Server is not installed or not working
- CPU target threshold is too high
- Application bottleneck is not CPU-related
- Cluster does not have enough available nodes

## Investigation Steps

1. Check HPA:

kubectl get hpa -n <namespace>

2. Describe HPA:

kubectl describe hpa <hpa-name> -n <namespace>

3. Check pod CPU usage:

kubectl top pods -n <namespace>

4. Check node capacity:

kubectl top nodes

5. Check deployment requests:

kubectl get deployment <deployment-name> -n <namespace> -o yaml

## Recommended Fixes

- Increase maxReplicas if the service reached the current maximum.
- Add CPU requests if missing.
- Lower CPU target if scaling happens too late.
- Add more cluster capacity if nodes are full.
- Investigate database or queue latency if CPU is normal.
