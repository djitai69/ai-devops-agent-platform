import json
import os
from pathlib import Path
from typing import Dict, List, Any, Set


METRICS_DIR = Path(os.getenv("METRICS_DIR", "/data/metrics"))

KNOWN_SERVICES = [
    "checkout-service",
    "payment-service",
    "auth-service",
]


def list_metric_files() -> List[str]:
    if not METRICS_DIR.exists():
        return []

    return sorted([p.name for p in METRICS_DIR.glob("*.json")])


def load_metrics_file(filename: str) -> Dict[str, Any]:
    file_path = METRICS_DIR / filename

    if not file_path.exists():
        return {}

    return json.loads(file_path.read_text(encoding="utf-8"))


def get_metrics_for_service(service_name: str) -> Dict[str, Any]:
    filename = f"{service_name}.json"
    return load_metrics_file(filename)


def detect_services_from_question(question: str) -> Set[str]:
    q = question.lower()
    services = set()

    for service in KNOWN_SERVICES:
        short_name = service.replace("-service", "")
        if service in q or short_name in q:
            services.add(service)

    return services


def detect_services_from_logs(log_context: str) -> Set[str]:
    text = log_context.lower()
    services = set()

    for service in KNOWN_SERVICES:
        if service in text:
            services.add(service)

    return services


def summarize_metric_findings(metrics: Dict[str, Any]) -> List[str]:
    findings = []

    service = metrics.get("service", "unknown-service")

    cpu = metrics.get("cpu_usage_percent")
    memory = metrics.get("memory_usage_percent")
    latency = metrics.get("latency_p95_ms")
    error_rate = metrics.get("error_rate_percent")
    pod_restarts = metrics.get("pod_restarts")

    if cpu is not None and cpu >= 85:
        findings.append(f"{service}: high CPU usage at {cpu}%")

    if memory is not None and memory >= 85:
        findings.append(f"{service}: high memory usage at {memory}%")

    if latency is not None and latency >= 1000:
        findings.append(f"{service}: high p95 latency at {latency}ms")

    if error_rate is not None and error_rate >= 5:
        findings.append(f"{service}: elevated error rate at {error_rate}%")

    if pod_restarts is not None and pod_restarts > 0:
        findings.append(f"{service}: pod restarts detected count={pod_restarts}")

    hpa_current = metrics.get("hpa_current_replicas")
    hpa_max = metrics.get("hpa_max_replicas")

    if hpa_current is not None and hpa_max is not None and hpa_current >= hpa_max:
        findings.append(
            f"{service}: HPA is at max replicas current={hpa_current} max={hpa_max}"
        )

    db_pool = metrics.get("db_connection_pool_usage_percent")
    if db_pool is not None and db_pool >= 85:
        findings.append(f"{service}: database connection pool usage high at {db_pool}%")

    db_query = metrics.get("db_query_p95_ms")
    if db_query is not None and db_query >= 1000:
        findings.append(f"{service}: slow database queries p95={db_query}ms")

    db_errors = metrics.get("db_connection_errors")
    if db_errors is not None and db_errors > 0:
        findings.append(f"{service}: database connection errors count={db_errors}")

    if not findings:
        findings.append(f"{service}: metrics look normal")

    return findings


def analyze_relevant_metrics(question: str, log_context: str = "") -> Dict[str, Any]:
    selected_services = detect_services_from_question(question)
    selected_services.update(detect_services_from_logs(log_context))

    if not selected_services:
        selected_services = set(KNOWN_SERVICES)

    service_metrics = []
    findings = []

    for service in sorted(selected_services):
        metrics = get_metrics_for_service(service)

        if not metrics:
            continue

        service_metrics.append(metrics)
        findings.extend(summarize_metric_findings(metrics))

    return {
        "services": sorted(selected_services),
        "metrics": service_metrics,
        "findings": findings,
    }
