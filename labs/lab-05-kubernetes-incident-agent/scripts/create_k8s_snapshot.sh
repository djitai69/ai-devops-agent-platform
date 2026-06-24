#!/usr/bin/env bash
set -euo pipefail

mkdir -p data/k8s

kubectl apply -f k8s/

echo "Waiting for Kubernetes events..."
sleep 10

kubectl get pods -n ai-sre-demo > data/k8s/pods.txt || true
kubectl get events -n ai-sre-demo --sort-by=.lastTimestamp > data/k8s/events.txt || true

PAYMENT_POD=$(kubectl get pod -n ai-sre-demo -l app=payment-service -o jsonpath='{.items[0].metadata.name}' || true)

if [ -n "$PAYMENT_POD" ]; then
  kubectl describe pod "$PAYMENT_POD" -n ai-sre-demo > data/k8s/describe-payment-service.txt || true
fi

echo "Kubernetes snapshot written to data/k8s/"
