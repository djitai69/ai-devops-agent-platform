# Lab 08 - Remediation Planner

This lab extends the AI DevOps/SRE platform with safe remediation planning.

The agent can now generate a human-reviewable remediation plan with:

- incident summary
- probable root cause
- proposed remediation commands
- safety notes
- risk level
- preconditions
- validation steps
- rollback plan
- human approval requirement

The agent does **not** apply changes automatically.

This lab follows a safe DevOps AI workflow:

```text
diagnose → recommend → plan → human approval → apply manually → validate

User
  ↓
FastAPI /chat
  ↓
LangGraph
  ├── classify_incident
  ├── retrieve_runbooks
  ├── analyze_logs
  ├── analyze_metrics
  ├── analyze_k8s
  ├── analyze_finops
  ├── devops_agent
  ├── remediation_plan
  └── chatops_report
  ↓
RCA / Remediation Plan / ChatOps Update

What This Lab Demonstrates

Lab 08 demonstrates:

safe remediation planning
deterministic remediation templates for known incident patterns
Kubernetes command generation
validation and rollback planning
human-in-the-loop approval
separation between diagnosis and execution
local live validation with k3d

The remediation planner is intentionally deterministic for known safety-critical patterns.
The LLM is useful for explanation, but remediation commands should be predictable, reviewable, and grounded in evidence.

Safety Model

The agent generates plans only.

It does not:

apply Kubernetes changes automatically
create Secrets automatically
restart deployments automatically
run production commands automatically
expose secret values

Human approval is required before any remediation command is applied.

AI recommends.
Human reviews.
Human applies.
System is validated.


Run the Local AI DevOps Stack

From this lab directory:

cd ~/ai-devops-agent-platform/labs/lab-08-remediation-planner

Start the stack:

docker compose up -d --build
docker stop ai-devops-open-webui

Make sure the required Ollama models are available:

docker exec -it ai-devops-ollama ollama pull qwen2.5:0.5b
docker exec -it ai-devops-ollama ollama pull nomic-embed-text

Ingest runbooks into Qdrant:

docker exec -it ai-devops-agent-api python ingest_runbooks.py

Check API health:

curl -sS http://localhost:8000/health
Generate a Remediation Plan
curl --max-time 30 -sS -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Generate a remediation plan to fix payment-service pod not starting"}' \
  | jq -r '
"ANSWER:\n" + (.answer // "NO ANSWER")
+ "\n\nSOURCES:\n"
+ ((.sources // []) | map("- " + .) | join("\n"))
'

Expected output includes:

# Remediation Plan

## Incident
## Root Cause
## Safety
## Preconditions
## Step 1 — Inspect Current State
## Step 2 — Apply Remediation
## Step 3 — Restart Workload
## Step 4 — Validate
## Rollback
## Human Approval Required
Example Remediation Output

The agent produces a plan like:

# Remediation Plan

## Incident

payment-service is blocked by a Kubernetes container configuration error.

## Root Cause

The workload expects Secret "payment-db-secret" with key "password".
Kubernetes evidence shows the Secret or required key was unavailable when the pod was created.

## Safety

Mode: Human-in-the-loop
Execution: Not automatic
Risk: Medium

Reason: updating Secrets can affect application startup and database connectivity.

The generated plan includes commands such as:

kubectl get secret payment-db-secret -n ai-sre-demo
kubectl create secret generic payment-db-secret \
  --from-literal=password='<REPLACE_WITH_REAL_PASSWORD>' \
  -n ai-sre-demo
kubectl rollout restart deployment/payment-service -n ai-sre-demo

It also includes validation and rollback commands.

Live k3d Kubernetes Demo

This lab can run in two modes:

Snapshot mode — the agent analyzes mock Kubernetes evidence from data/k8s.
Live k3d mode — you create a real local Kubernetes cluster, namespace, Secret, and deployment to validate the remediation commands.

The mock evidence represents the original failure:

CreateContainerConfigError
secret "payment-db-secret" not found

The live k3d demo validates the remediation path manually.

Install k3d
Linux / WSL
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

Validate:

k3d version
Create Local Kubernetes Cluster
k3d cluster create ai-sre-agent

Validate cluster context:

kubectl config current-context
kubectl get nodes

Expected current context:

k3d-ai-sre-agent

At least one node should be Ready.

Create Demo Namespace
kubectl create namespace ai-sre-demo

Validate:

kubectl get ns ai-sre-demo

Expected:

NAME          STATUS   AGE
ai-sre-demo   Active   ...
Create Required Secret

The demo payment-service expects a Kubernetes Secret named:

payment-db-secret

with a key named:

password

Create the Secret:

kubectl create secret generic payment-db-secret \
  --from-literal=password='password' \
  -n ai-sre-demo

Validate the Secret exists:

kubectl get secret payment-db-secret -n ai-sre-demo

Expected:

NAME                TYPE     DATA   AGE
payment-db-secret   Opaque   1      ...

Validate the key exists without printing the secret value:

kubectl get secret payment-db-secret -n ai-sre-demo -o jsonpath='{.data.password}' | wc -c

Expected: a number greater than 0.

Deploy payment-service

Create a live demo manifest:

mkdir -p k8s/live-demo

cat > k8s/live-demo/payment-service.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: ai-sre-demo
  labels:
    app: payment-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
    spec:
      containers:
        - name: payment-service
          image: nginx:latest
          ports:
            - containerPort: 80
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: payment-db-secret
                  key: password
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: payment-service
  namespace: ai-sre-demo
  labels:
    app: payment-service
spec:
  selector:
    app: payment-service
  ports:
    - name: http
      port: 80
      targetPort: 80
YAML

Apply it:

kubectl apply -f k8s/live-demo/payment-service.yaml

Validate:

kubectl get deployment payment-service -n ai-sre-demo
kubectl get pods -n ai-sre-demo
kubectl rollout status deployment/payment-service -n ai-sre-demo

Expected:

deployment "payment-service" successfully rolled out

Check the pod details:

kubectl describe pod -n ai-sre-demo -l app=payment-service

You should see that DB_PASSWORD is loaded from the Secret:

DB_PASSWORD: <set to the key 'password' in secret 'payment-db-secret'> Optional: false
Validate the Live Remediation State

After creating the Secret and deployment, validate the live cluster:

kubectl get secret payment-db-secret -n ai-sre-demo
kubectl get deployment payment-service -n ai-sre-demo
kubectl get pods -n ai-sre-demo
kubectl rollout status deployment/payment-service -n ai-sre-demo
kubectl get events -n ai-sre-demo --sort-by=.lastTimestamp

Expected:

- Secret exists
- deployment exists
- payment-service pod is Running
- rollout is successful
- no current missing Secret errors
Optional: Simulate the Original Failure

To reproduce the missing Secret incident in the live cluster, delete the Secret:

kubectl delete secret payment-db-secret -n ai-sre-demo

Restart the deployment:

kubectl rollout restart deployment/payment-service -n ai-sre-demo

Check pod status:

kubectl get pods -n ai-sre-demo

Check details:

kubectl describe pod -n ai-sre-demo -l app=payment-service

Check recent events:

kubectl get events -n ai-sre-demo --sort-by=.lastTimestamp

Expected failure pattern:

CreateContainerConfigError
secret "payment-db-secret" not found
Apply the Remediation Manually

Recreate the Secret:

kubectl create secret generic payment-db-secret \
  --from-literal=password='password' \
  -n ai-sre-demo

Restart the deployment:

kubectl rollout restart deployment/payment-service -n ai-sre-demo

Validate rollout:

kubectl rollout status deployment/payment-service -n ai-sre-demo
kubectl get pods -n ai-sre-demo
kubectl get events -n ai-sre-demo --sort-by=.lastTimestamp

Expected result:

- payment-service pod returns to Running
- rollout completes successfully
- missing Secret error is gone
Update an Existing Secret Safely

If the Secret exists but the value or key needs to be corrected, use a dry-run apply pattern:

kubectl create secret generic payment-db-secret \
  --from-literal=password='<REPLACE_WITH_REAL_PASSWORD>' \
  -n ai-sre-demo \
  --dry-run=client -o yaml | kubectl apply -f -

Then restart and validate:

kubectl rollout restart deployment/payment-service -n ai-sre-demo
kubectl rollout status deployment/payment-service -n ai-sre-demo
kubectl get pods -n ai-sre-demo
Test ChatOps With Remediation

If Lab 07 Slack webhook support is configured, you can generate a remediation-aware ChatOps update:

curl --max-time 60 -sS -X POST http://localhost:8000/chatops/send \
  -H "Content-Type: application/json" \
  -d '{"question": "Write a Slack update with a remediation plan: payment-service pod is not starting"}' \
  | jq -r '
"ANSWER:\n" + (.answer // "NO ANSWER")
+ "\n\nSOURCES:\n"
+ ((.sources // []) | map("- " + .) | join("\n"))
'

If SLACK_WEBHOOK_URL is configured in .env, the update is sent to Slack.

If it is not configured, the API returns the generated update and reports:

Slack delivery: skipped. Reason: SLACK_WEBHOOK_URL is not configured.
Environment Variables

Use .env for local runtime configuration.

Example:

OLLAMA_MODEL=qwen2.5:0.5b
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://ollama:11434/v1
OLLAMA_HOST=http://ollama:11434
QDRANT_COLLECTION=devops_runbooks
SLACK_WEBHOOK_URL=

If using Slack, set:

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

Do not commit real webhook URLs.

Troubleshooting
kubectl connects to localhost:8080

Error:

dial tcp 127.0.0.1:8080: connect: connection refused

Cause:

kubectl has no valid Kubernetes context or the local cluster is not running.

Fix:

k3d cluster create ai-sre-agent
kubectl config current-context
kubectl get nodes
Secret already exists

Error:

Error from server (AlreadyExists): secrets "payment-db-secret" already exists

Use the safe update pattern:

kubectl create secret generic payment-db-secret \
  --from-literal=password='<REPLACE_WITH_REAL_PASSWORD>' \
  -n ai-sre-demo \
  --dry-run=client -o yaml | kubectl apply -f -
Agent API returns model not found

Error:

model 'llama3.2:3b' not found

Fix .env:

OLLAMA_MODEL=qwen2.5:0.5b

Recreate containers:

docker compose down
docker compose up -d --build --force-recreate

Check the model:

docker exec -it ai-devops-agent-api env | grep OLLAMA_MODEL
docker exec -it ai-devops-ollama ollama list

Pull if missing:

docker exec -it ai-devops-ollama ollama pull qwen2.5:0.5b
curl times out

If /chat times out, the LLM may be slow or unavailable.

For known remediation patterns, this lab uses deterministic remediation planning to avoid depending on the LLM for safety-critical commands.

Check logs:

docker logs ai-devops-agent-api --tail=120
docker logs ai-devops-ollama --tail=120
Cleanup

Delete the demo namespace:

kubectl delete namespace ai-sre-demo

Delete the k3d cluster:

k3d cluster delete ai-sre-agent

Stop the Docker stack:

docker compose down
Portfolio Explanation

In Lab 08, I added a safe remediation planner to the AI DevOps Agent Platform.

The agent can generate reviewable Kubernetes remediation commands, validation steps, rollback instructions, risk level, and an explicit human approval requirement.

The agent does not execute production changes automatically.
For known safety-critical patterns, such as a Kubernetes deployment blocked by a missing Secret, the remediation plan is deterministic rather than freely generated by the LLM.

This keeps the workflow safer, more explainable, and closer to how real SRE teams operate.

Key Takeaway
AI should not blindly fix production.
AI should produce a safe, reviewable plan.
Humans approve and apply.
The system is validated after the change.
