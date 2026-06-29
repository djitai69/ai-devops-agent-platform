# Lab 09 - Approval-Gated Remediation Executor

This lab extends the AI DevOps/SRE platform with a safe, approval-gated remediation executor.

In previous labs, the platform could diagnose incidents, generate RCA reports, create ChatOps updates, and produce human-reviewable remediation plans.

In this lab, the platform adds a controlled execution layer:

```text
Remediation Plan
  ↓
Action Preview
  ↓
Human Approval
  ↓
Allowlist Check
  ↓
Safe Kubernetes Execution
  ↓
Audit Log
```

The agent does **not** execute arbitrary shell commands.
It can only execute predefined, allowlisted Kubernetes actions after explicit approval.

---

## Goal

Build a safe remediation execution layer that can:

* preview a Kubernetes action before execution
* require explicit human approval
* block unknown or dangerous actions
* restrict execution to an allowed namespace
* redact secret values from returned commands and logs
* execute only predefined safe actions
* write every attempted action to an audit log

---

## Safety Model

This lab follows a human-in-the-loop DevOps AI model:

```text
AI recommends.
Human reviews.
Human approves.
Executor validates.
Executor runs only allowlisted actions.
System records an audit trail.
```

The executor does **not** allow:

* raw shell commands
* arbitrary `kubectl` commands
* destructive namespace deletion
* cluster-wide actions
* unknown YAML apply commands
* `curl | bash`
* commands outside the allowed namespace
* unapproved remediation execution

---

## Allowed Namespace

The executor is restricted to:

```text
ai-sre-demo
```

Requests for other namespaces, such as `production`, are blocked.

---

## Allowed Actions

The executor supports only these allowlisted actions:

```text
get_pods
get_events
get_secret_metadata
rollout_status
restart_deployment
create_demo_secret
```

Risk levels:

| Action                |   Risk | Description                                             |
| --------------------- | -----: | ------------------------------------------------------- |
| `get_pods`            |    Low | Read pod state in the demo namespace                    |
| `get_events`          |    Low | Read recent Kubernetes events                           |
| `get_secret_metadata` |    Low | Read Secret metadata only                               |
| `rollout_status`      |    Low | Check deployment rollout status                         |
| `restart_deployment`  | Medium | Restart a specific deployment                           |
| `create_demo_secret`  | Medium | Create or update a demo Secret using safe apply pattern |

---

## Architecture

```text
User / Operator
  ↓
FastAPI
  ├── POST /actions/preview
  ├── POST /actions/execute
  └── GET  /actions/history
  ↓
Action Executor
  ├── validate action
  ├── validate namespace
  ├── build safe command
  ├── redact secret values
  ├── require approval
  ├── execute allowlisted kubectl command
  └── write audit log
  ↓
Local k3d Kubernetes Cluster
```

---

## New Files

```text
app/action_executor.py
```

This file contains:

* action allowlist
* namespace restrictions
* command builder
* risk classification
* secret redaction
* preview logic
* execution logic
* audit log writer
* action history reader

---

## API Endpoints

### Preview action

```text
POST /actions/preview
```

Builds and returns the command that would run, but does not execute it.

### Execute action

```text
POST /actions/execute
```

Executes the action only if:

* the action is allowlisted
* the namespace is allowed
* required parameters are valid
* `approved` is set to `true`

### Action history

```text
GET /actions/history
```

Returns recent attempted and executed actions from the audit log.

---

## Environment Requirements

This lab assumes:

* Docker is running
* k3d is installed
* a local k3d cluster exists
* namespace `ai-sre-demo` exists
* `payment-service` deployment exists
* `payment-db-secret` Secret exists or can be created
* the API container has access to kubeconfig
* the API container includes `kubectl`

---

## Run the Local Stack

From this lab directory:

```bash
cd ~/ai-devops-agent-platform/labs/lab-09-approval-gated-executor
```

Start the stack:

```bash
docker compose up -d --build
docker stop ai-devops-open-webui
```

Make sure the required Ollama models are available:

```bash
docker exec -it ai-devops-ollama ollama pull qwen2.5:0.5b
docker exec -it ai-devops-ollama ollama pull nomic-embed-text
```

Ingest runbooks:

```bash
docker exec -it ai-devops-agent-api python ingest_runbooks.py
```

Health check:

```bash
curl -sS http://localhost:8000/health
```

---

## Kubeconfig Mount

The `agent-api` container needs access to the local Kubernetes config.

In `docker-compose.yml`, the `agent-api` service should include:

```yaml
volumes:
  - ./app:/app
  - ./docs:/docs
  - ./data:/app/data
  - ~/.kube:/root/.kube:ro
```

The kubeconfig is mounted read-only.

---

## kubectl in the API Container

The API container needs `kubectl`.

The Dockerfile should install it, for example:

```dockerfile
RUN apt-get update && apt-get install -y curl ca-certificates \
    && curl -LO "https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

Validate:

```bash
docker exec -it ai-devops-agent-api kubectl version --client
docker exec -it ai-devops-agent-api kubectl config current-context
```

Expected context:

```text
k3d-ai-sre-agent
```

---

## Live k3d Demo Setup

If the cluster is not already running, create it:

```bash
k3d cluster create ai-sre-agent
```

Validate:

```bash
kubectl config current-context
kubectl get nodes
```

Create namespace:

```bash
kubectl create namespace ai-sre-demo
```

Create demo Secret:

```bash
kubectl create secret generic payment-db-secret \
  --from-literal=password='password' \
  -n ai-sre-demo
```

Create demo deployment:

```bash
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
```

Apply:

```bash
kubectl apply -f k8s/live-demo/payment-service.yaml
```

Validate:

```bash
kubectl get secret payment-db-secret -n ai-sre-demo
kubectl get deployment payment-service -n ai-sre-demo
kubectl get pods -n ai-sre-demo
kubectl rollout status deployment/payment-service -n ai-sre-demo
```

---

## Test 1 - Preview a Safe Action

Preview a deployment restart:

```bash
curl -sS -X POST http://localhost:8000/actions/preview \
  -H "Content-Type: application/json" \
  -d '{
    "action": "restart_deployment",
    "namespace": "ai-sre-demo",
    "deployment": "payment-service"
  }' | jq
```

Expected behavior:

```text
Preview only. No command was executed.
```

Expected response includes:

```json
{
  "action": "restart_deployment",
  "namespace": "ai-sre-demo",
  "approved": false,
  "will_execute": false,
  "risk": "medium"
}
```

---

## Test 2 - Block Execution Without Approval

```bash
curl -sS -X POST http://localhost:8000/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "restart_deployment",
    "namespace": "ai-sre-demo",
    "deployment": "payment-service",
    "approved": false
  }' | jq
```

Expected:

```json
{
  "approved": false,
  "executed": false,
  "stderr": "Action was not approved. No command was executed."
}
```

This confirms that the executor refuses to run even an allowlisted action unless approval is explicit.

---

## Test 3 - Execute Approved Safe Action

```bash
curl -sS -X POST http://localhost:8000/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "restart_deployment",
    "namespace": "ai-sre-demo",
    "deployment": "payment-service",
    "approved": true
  }' | jq
```

Expected response includes:

```json
{
  "action": "restart_deployment",
  "approved": true,
  "executed": true,
  "risk": "medium",
  "returncode": 0
}
```

Validate in Kubernetes:

```bash
kubectl rollout status deployment/payment-service -n ai-sre-demo
kubectl get pods -n ai-sre-demo
```

---

## Test 4 - Preview Secret Creation / Update

```bash
curl -sS -X POST http://localhost:8000/actions/preview \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_demo_secret",
    "namespace": "ai-sre-demo",
    "secret_name": "payment-db-secret",
    "secret_key": "password",
    "secret_value": "password"
  }' | jq
```

The returned command should redact the secret value:

```text
--from-literal=<REDACTED>
```

---

## Test 5 - Execute Approved Secret Creation / Update

```bash
curl -sS -X POST http://localhost:8000/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_demo_secret",
    "namespace": "ai-sre-demo",
    "secret_name": "payment-db-secret",
    "secret_key": "password",
    "secret_value": "password",
    "approved": true
  }' | jq
```

Validate:

```bash
kubectl get secret payment-db-secret -n ai-sre-demo
```

The executor uses a safer idempotent pattern:

```text
kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -
```

---

## Test 6 - Block Disallowed Namespace

This request should be blocked:

```bash
curl -sS -X POST http://localhost:8000/actions/preview \
  -H "Content-Type: application/json" \
  -d '{
    "action": "restart_deployment",
    "namespace": "production",
    "deployment": "payment-service"
  }' | jq
```

Expected behavior:

```text
Namespace 'production' is not allowed.
```

Only `ai-sre-demo` is allowed.

---

## Test 7 - Block Unknown Action

This request should be blocked:

```bash
curl -sS -X POST http://localhost:8000/actions/preview \
  -H "Content-Type: application/json" \
  -d '{
    "action": "delete_namespace",
    "namespace": "ai-sre-demo"
  }' | jq
```

Expected behavior:

```text
Action 'delete_namespace' is not allowed.
```

---

## Test 8 - Read Action History

```bash
curl -sS http://localhost:8000/actions/history | jq
```

The response should include recent attempted and executed actions.

The audit log includes:

* timestamp
* action
* namespace
* approval status
* execution status
* risk level
* redacted command
* stdout
* stderr
* return code

---

## Audit Log

The executor writes action records to:

```text
/app/data/action_audit_log.jsonl
```

Because `./data` is mounted into the container, the log is persisted locally under:

```text
data/action_audit_log.jsonl
```

View it locally:

```bash
tail -n 20 data/action_audit_log.jsonl
```

---

## Example Action Request

```json
{
  "action": "restart_deployment",
  "namespace": "ai-sre-demo",
  "deployment": "payment-service",
  "approved": true
}
```

This maps to:

```bash
kubectl rollout restart deployment/payment-service -n ai-sre-demo
```

---

## Example Blocked Request

```json
{
  "action": "delete_namespace",
  "namespace": "ai-sre-demo",
  "approved": true
}
```

This is blocked because `delete_namespace` is not in the action allowlist.

---

## Troubleshooting

### Container cannot find kubectl

Check:

```bash
docker exec -it ai-devops-agent-api kubectl version --client
```

If missing, confirm the Dockerfile installs `kubectl`, then rebuild:

```bash
docker compose down
docker compose up -d --build --force-recreate
```

---

### Container cannot access k3d cluster

Check from inside the container:

```bash
docker exec -it ai-devops-agent-api kubectl config current-context
docker exec -it ai-devops-agent-api kubectl get nodes
```

If this fails, confirm that `~/.kube` is mounted:

```yaml
- ~/.kube:/root/.kube:ro
```

Then recreate the container:

```bash
docker compose down
docker compose up -d --build --force-recreate
```

---

### Namespace is blocked

Only this namespace is allowed:

```text
ai-sre-demo
```

This is intentional. It prevents the demo executor from touching production-like namespaces.

---

### Secret value appears in output

The executor should redact values from returned commands.

If secret values appear in API responses or logs, do not commit the output. Fix `redact_command()` in `app/action_executor.py`.

---

## Cleanup

Delete the demo namespace:

```bash
kubectl delete namespace ai-sre-demo
```

Delete the local k3d cluster:

```bash
k3d cluster delete ai-sre-agent
```

Stop the Docker stack:

```bash
docker compose down
```

---

## Portfolio Explanation

In Lab 09, I added an approval-gated remediation executor to the AI DevOps Agent Platform.

The platform can now execute only predefined, allowlisted Kubernetes actions after explicit human approval. Dangerous or unknown actions are blocked, namespaces are restricted, secret values are redacted, and every attempted action is written to an audit log.

This demonstrates a safer path from AI-generated remediation plans to controlled operational execution.

---

## Key Takeaway

```text
AI-generated remediation should not mean unrestricted automation.

A safe DevOps AI system needs:
- human approval
- action allowlists
- namespace restrictions
- secret redaction
- audit logs
- rollback-aware workflows
```
