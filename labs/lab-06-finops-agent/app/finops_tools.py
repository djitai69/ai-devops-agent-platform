import csv
import os
from pathlib import Path
from typing import Dict, List, Any


FINOPS_DIR = Path(os.getenv("FINOPS_DIR", "/data/finops"))


def read_csv_file(filename: str) -> List[Dict[str, str]]:
    file_path = FINOPS_DIR / filename

    if not file_path.exists():
        return []

    with file_path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def calculate_recommended_cpu_request(cpu_p95_millicores: int) -> int:
    """
    Recommend CPU request with a safety buffer above p95.
    Round to common Kubernetes-friendly values.
    """

    recommendation = int(cpu_p95_millicores * 1.25)

    if recommendation <= 100:
        return 100
    if recommendation <= 250:
        return 250
    if recommendation <= 500:
        return 500
    if recommendation <= 750:
        return 750
    if recommendation <= 1000:
        return 1000
    if recommendation <= 1500:
        return 1500

    return recommendation


def calculate_recommended_memory_request(memory_p95_mb: int) -> int:
    """
    Recommend memory request with a safety buffer above p95.
    Round to common values.
    """

    recommendation = int(memory_p95_mb * 1.25)

    if recommendation <= 256:
        return 256
    if recommendation <= 512:
        return 512
    if recommendation <= 1024:
        return 1024
    if recommendation <= 1536:
        return 1536
    if recommendation <= 2048:
        return 2048
    if recommendation <= 3072:
        return 3072
    if recommendation <= 4096:
        return 4096

    return recommendation


def analyze_workload_rightsizing() -> List[Dict[str, Any]]:
    rows = read_csv_file("k8s-requests-usage.csv")
    findings = []

    for row in rows:
        cpu_request = to_int(row["cpu_request_millicores"])
        cpu_avg = to_int(row["cpu_avg_millicores"])
        cpu_p95 = to_int(row["cpu_p95_millicores"])

        memory_request = to_int(row["memory_request_mb"])
        memory_avg = to_int(row["memory_avg_mb"])
        memory_p95 = to_int(row["memory_p95_mb"])

        monthly_cost = to_int(row["monthly_cost_usd"])

        recommended_cpu = calculate_recommended_cpu_request(cpu_p95)
        recommended_memory = calculate_recommended_memory_request(memory_p95)

        cpu_waste_percent = 0
        memory_waste_percent = 0

        if cpu_request > 0:
            cpu_waste_percent = round((1 - (cpu_p95 / cpu_request)) * 100, 1)

        if memory_request > 0:
            memory_waste_percent = round((1 - (memory_p95 / memory_request)) * 100, 1)

        should_rightsize_cpu = recommended_cpu < cpu_request
        should_rightsize_memory = recommended_memory < memory_request

        estimated_savings = 0

        if should_rightsize_cpu or should_rightsize_memory:
            waste_factor = max(cpu_waste_percent, memory_waste_percent) / 100
            estimated_savings = round(monthly_cost * min(waste_factor, 0.65), 2)

        if should_rightsize_cpu or should_rightsize_memory:
            findings.append(
                {
                    "type": "workload_rightsizing",
                    "namespace": row["namespace"],
                    "workload": row["workload"],
                    "current_cpu_request_millicores": cpu_request,
                    "cpu_avg_millicores": cpu_avg,
                    "cpu_p95_millicores": cpu_p95,
                    "recommended_cpu_request_millicores": recommended_cpu,
                    "current_memory_request_mb": memory_request,
                    "memory_avg_mb": memory_avg,
                    "memory_p95_mb": memory_p95,
                    "recommended_memory_request_mb": recommended_memory,
                    "current_monthly_cost_usd": monthly_cost,
                    "estimated_monthly_savings_usd": estimated_savings,
                    "risk": "medium" if row["namespace"] == "production" else "low",
                    "recommendation": (
                        "Reduce requests gradually and monitor latency, errors, restarts, "
                        "CPU throttling, and OOMKilled events for at least 7 days."
                    ),
                }
            )

    return findings


def analyze_idle_resources() -> List[Dict[str, Any]]:
    rows = read_csv_file("idle-resources.csv")
    findings = []

    for row in rows:
        monthly_cost = to_int(row["monthly_cost_usd"])
        last_used_days = to_int(row["last_used_days_ago"])

        if last_used_days >= 30:
            findings.append(
                {
                    "type": "idle_resource",
                    "resource_type": row["resource_type"],
                    "name": row["name"],
                    "namespace": row["namespace"],
                    "age_days": to_int(row["age_days"]),
                    "last_used_days_ago": last_used_days,
                    "estimated_monthly_savings_usd": monthly_cost,
                    "recommendation": row["recommendation"],
                    "risk": "high" if row["namespace"] == "production" else "low",
                }
            )

    return findings


def analyze_node_utilization() -> List[Dict[str, Any]]:
    rows = read_csv_file("node-utilization.csv")
    findings = []

    for row in rows:
        cpu_allocatable = to_int(row["cpu_allocatable_millicores"])
        cpu_avg = to_int(row["cpu_avg_millicores"])
        memory_allocatable = to_int(row["memory_allocatable_mb"])
        memory_avg = to_int(row["memory_avg_mb"])
        monthly_cost = to_int(row["monthly_cost_usd"])

        cpu_utilization = round((cpu_avg / cpu_allocatable) * 100, 1) if cpu_allocatable else 0
        memory_utilization = round((memory_avg / memory_allocatable) * 100, 1) if memory_allocatable else 0

        if cpu_utilization < 35 and memory_utilization < 40:
            findings.append(
                {
                    "type": "node_underutilization",
                    "node": row["node"],
                    "node_type": row["node_type"],
                    "cpu_utilization_percent": cpu_utilization,
                    "memory_utilization_percent": memory_utilization,
                    "current_monthly_cost_usd": monthly_cost,
                    "estimated_monthly_savings_usd": round(monthly_cost * 0.35, 2),
                    "recommendation": (
                        "Review binpacking and consider reducing node count, using smaller nodes, "
                        "or moving suitable workloads to cheaper instance families."
                    ),
                    "risk": "medium",
                }
            )

    return findings


def analyze_finops() -> Dict[str, Any]:
    workload_findings = analyze_workload_rightsizing()
    idle_findings = analyze_idle_resources()
    node_findings = analyze_node_utilization()

    all_findings = workload_findings + idle_findings + node_findings

    total_savings = round(
        sum(float(item.get("estimated_monthly_savings_usd", 0)) for item in all_findings),
        2,
    )

    top_findings = sorted(
        all_findings,
        key=lambda item: float(item.get("estimated_monthly_savings_usd", 0)),
        reverse=True,
    )

    return {
        "summary": {
            "finding_count": len(all_findings),
            "estimated_total_monthly_savings_usd": total_savings,
        },
        "findings": top_findings,
    }


def format_finops_report() -> str:
    result = analyze_finops()
    summary = result["summary"]
    findings = result["findings"]

    lines = []

    lines.append("1. Cost Summary")
    lines.append("")
    lines.append(
        f"The cluster has {summary['finding_count']} cost optimization findings "
        f"with estimated total monthly savings of "
        f"${summary['estimated_total_monthly_savings_usd']}."
    )
    lines.append("")

    lines.append("2. Top Savings Opportunities")
    lines.append("")

    for item in findings[:6]:
        finding_type = item.get("type")

        if finding_type == "workload_rightsizing":
            lines.append(
                f"- {item['namespace']}/{item['workload']}: "
                f"current CPU request {item['current_cpu_request_millicores']}m, "
                f"p95 CPU {item['cpu_p95_millicores']}m, "
                f"recommended CPU request {item['recommended_cpu_request_millicores']}m. "
                f"Current memory request {item['current_memory_request_mb']}MB, "
                f"p95 memory {item['memory_p95_mb']}MB, "
                f"recommended memory request {item['recommended_memory_request_mb']}MB. "
                f"Estimated savings: ${item['estimated_monthly_savings_usd']}/month. "
                f"Risk: {item['risk']}."
            )

        elif finding_type == "idle_resource":
            lines.append(
                f"- {item['namespace']}/{item['name']} ({item['resource_type']}): "
                f"idle for {item['last_used_days_ago']} days. "
                f"Recommendation: {item['recommendation']}. "
                f"Estimated savings: ${item['estimated_monthly_savings_usd']}/month. "
                f"Risk: {item['risk']}."
            )

        elif finding_type == "node_underutilization":
            lines.append(
                f"- {item['node']} ({item['node_type']}): "
                f"CPU utilization {item['cpu_utilization_percent']}%, "
                f"memory utilization {item['memory_utilization_percent']}%. "
                f"Recommendation: {item['recommendation']} "
                f"Estimated savings: ${item['estimated_monthly_savings_usd']}/month. "
                f"Risk: {item['risk']}."
            )

    lines.append("")
    lines.append("3. Recommended Actions")
    lines.append("")
    lines.append("- Prioritize non-production and idle resources first.")
    lines.append("- Review and delete unused persistent volumes, snapshots, and load balancers after ownership validation.")
    lines.append("- Right-size overprovisioned CPU and memory requests gradually.")
    lines.append("- Review underutilized nodes for binpacking or node-count reduction.")
    lines.append("- Do not apply production changes automatically.")
    lines.append("")

    lines.append("4. Risk and Safety Notes")
    lines.append("")
    lines.append("- Production workloads should be changed gradually and reviewed by a human.")
    lines.append("- Keep memory requests above p95 usage with a safety buffer to avoid OOMKilled events.")
    lines.append("- Monitor latency, errors, restarts, CPU throttling, and saturation after changes.")
    lines.append("- Validate idle resources before deletion.")
    lines.append("")

    lines.append("5. Validation Plan")
    lines.append("")
    lines.append("- Compare CPU and memory p95 usage before and after rightsizing.")
    lines.append("- Monitor workloads for at least 7 days after changes.")
    lines.append("- Confirm no increase in latency, errors, restarts, or OOMKilled events.")
    lines.append("- Track realized monthly savings after cleanup or rightsizing.")

    return "\n".join(lines)
