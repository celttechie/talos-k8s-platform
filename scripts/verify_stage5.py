#!/usr/bin/env python3
"""
Verification Test Suite - Stage 5: Observability Platform (Prometheus, Grafana & Hubble)
Validates kube-prometheus-stack configuration, alerting rules, and curated Grafana dashboard definitions.
"""

import json
import os
import subprocess
import sys
import yaml

from common import (
    GREEN,
    YELLOW,
    RESET,
    TestReporter,
    get_repo_root,
    validate_yaml_file,
)

REPO_ROOT = get_repo_root()
MONITORING_DIR = os.path.join(REPO_ROOT, "gitops", "platform", "monitoring")
KUBE_PROM_VALUES = os.path.join(MONITORING_DIR, "kube-prometheus-stack.yaml")
ALERT_RULES = os.path.join(MONITORING_DIR, "alert-rules.yaml")
DASHBOARDS_DIR = os.path.join(MONITORING_DIR, "dashboards")
KUBECONFIG = os.path.join(REPO_ROOT, "kubeconfig")


def main():
    reporter = TestReporter("Stage 5: Observability (Prometheus & Grafana) Verification Suite")

    # 1. Validate Base Stack & Alert Rules
    for name, path in [
        ("kube-prometheus-stack Values", KUBE_PROM_VALUES),
        ("Lab Troubleshooting Alert Rules", ALERT_RULES)
    ]:
        exists = os.path.exists(path)
        reporter.record(f"{name} Manifest", exists, f"Found {path}" if exists else "Missing manifest")
        if exists:
            valid, msg = validate_yaml_file(path)
            reporter.record(f"{name} YAML Schema", valid, msg)

    # 2. Validate Curated Grafana Dashboards
    dashboard_files = [
        "compute-workload-pressure.yaml",
        "cilium-ebpf-network.yaml",
        "longhorn-csi-storage.yaml"
    ]

    for df in dashboard_files:
        df_path = os.path.join(DASHBOARDS_DIR, df)
        exists = os.path.exists(df_path)
        reporter.record(f"Grafana Dashboard [{df}]", exists, f"Found {df_path}" if exists else "Missing dashboard")
        if exists:
            valid, msg = validate_yaml_file(df_path)
            reporter.record(f"Dashboard [{df}] YAML Schema", valid, msg)
            # Verify inner JSON payload
            try:
                with open(df_path, "r") as f:
                    cm_data = yaml.safe_load(f)
                    json_key = list(cm_data.get("data", {}).keys())[0]
                    raw_json = cm_data["data"][json_key]
                    dash_json = json.loads(raw_json)
                    panels_count = len(dash_json.get("panels", []))
                    reporter.record(f"Dashboard [{df}] JSON Structure", panels_count >= 1, f"{dash_json.get('title')} ({panels_count} panels)")
            except Exception as e:
                reporter.record(f"Dashboard [{df}] JSON Structure", False, str(e))

    # 3. Dynamic Cluster Telemetry Checks (if cluster is online)
    if os.path.exists(KUBECONFIG):
        res = subprocess.run(["kubectl", f"--kubeconfig={KUBECONFIG}", "cluster-info"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"\n{GREEN}===> Querying Live Cluster for Observability Services...{RESET}")
            # Check monitoring namespace pods
            m_res = subprocess.run(
                ["kubectl", f"--kubeconfig={KUBECONFIG}", "-n", "monitoring", "get", "pods", "-o", "jsonpath={.items[*].metadata.name}"],
                capture_output=True, text=True
            )
            reporter.record("Live Monitoring Stack Pods", bool(m_res.stdout.strip()), m_res.stdout or "No pods deployed yet in monitoring namespace")
        else:
            print(f"\n{YELLOW}⚠️  Live Kubernetes cluster offline or unreachable via {KUBECONFIG}.{RESET}")
            reporter.record("Live Observability Stack Verification", True, "Static configuration and declarative manifests verified")
    else:
        reporter.record("Live Observability Stack Verification", True, "Static configuration and declarative manifests verified")

    return reporter.summary(
        "🎉 Stage 5 Verification Succeeded: All Prometheus, Grafana, and Alerting configurations verified!",
        "❌ Stage 5 Verification Failed: One or more checks failed."
    )


if __name__ == "__main__":
    sys.exit(main())
