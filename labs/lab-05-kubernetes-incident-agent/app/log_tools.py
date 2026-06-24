import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Set


LOG_DIR = Path(os.getenv("LOG_DIR", "/data/logs"))

KNOWN_SERVICES = [
    "checkout-service",
    "payment-service",
    "auth-service",
]


IMPORTANT_TERMS = [
    "error",
    "warn",
    "timeout",
    "failed",
    "exhausted",
    "slow",
    "latency",
    "degraded",
    "retry",
]


def list_log_files() -> List[str]:
    if not LOG_DIR.exists():
        return []

    return sorted([p.name for p in LOG_DIR.glob("*.log")])


def read_log_file(filename: str) -> List[str]:
    file_path = LOG_DIR / filename

    if not file_path.exists():
        return []

    return file_path.read_text(encoding="utf-8").splitlines()


def search_logs(
    service_name: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, str]]:
    results = []
    log_files = list_log_files()

    for log_file in log_files:
        if service_name and service_name not in log_file:
            continue

        lines = read_log_file(log_file)

        for line in lines:
            line_lower = line.lower()

            if keyword:
                if keyword.lower() not in line_lower:
                    continue
            else:
                if not any(term in line_lower for term in IMPORTANT_TERMS):
                    continue

            results.append(
                {
                    "source": log_file,
                    "line": line,
                }
            )

            if len(results) >= limit:
                return results

    return results


def detect_services_from_question(question: str) -> Set[str]:
    q = question.lower()
    services = set()

    for service in KNOWN_SERVICES:
        short_name = service.replace("-service", "")
        if service in q or short_name in q:
            services.add(service)

    return services


def detect_services_from_log_lines(log_results: List[Dict[str, str]]) -> Set[str]:
    services = set()

    for item in log_results:
        line = item["line"].lower()

        for service in KNOWN_SERVICES:
            if service in line:
                services.add(service)

    return services


def deduplicate_logs(log_results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    unique = []

    for item in log_results:
        key = (item["source"], item["line"])

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


def search_relevant_logs(question: str, limit: int = 40) -> List[Dict[str, str]]:
    """
    Search logs in two passes.

    Pass 1:
    Search logs for services mentioned in the user question.

    Pass 2:
    If those logs mention downstream services, search those logs too.

    Example:
    Question mentions checkout-service.
    checkout-service log mentions payment-service.
    Then search payment-service logs as well.
    """

    selected_services = detect_services_from_question(question)

    if not selected_services:
        selected_services = set(KNOWN_SERVICES)

    first_pass_results = []

    for service in selected_services:
        first_pass_results.extend(
            search_logs(service_name=service, keyword=None, limit=limit)
        )

    downstream_services = detect_services_from_log_lines(first_pass_results)

    all_services = selected_services.union(downstream_services)

    second_pass_results = []

    for service in all_services:
        second_pass_results.extend(
            search_logs(service_name=service, keyword=None, limit=limit)
        )

    all_results = deduplicate_logs(first_pass_results + second_pass_results)

    return all_results[:limit]
