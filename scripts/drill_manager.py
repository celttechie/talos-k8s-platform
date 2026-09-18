#!/usr/bin/env python3
"""
Kubernetes Troubleshooting Drill Manager
Injects, verifies, and heals common cluster and workload failures for hands-on learning.
"""

import argparse
import sys
import time

from common import (
    BLUE,
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    run_cmd,
)

SCENARIOS = {
    "comp-oom-killed": {
        "domain": "Compute",
        "title": "Out Of Memory (OOMKilled / Exit 137)",
        "description": "Injects a memory leak loop into queue-worker causing it to exceed memory limit.",
        "inject_cmds": [
            """kubectl set env deployment/queue-worker -n training INJECT_LEAK=true --overwrite""",
            """kubectl patch deployment queue-worker -n training --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["/bin/sh","-c","python3 -c \\"import time; b=[]; print(\'Leaking memory...\'); [b.append(\'X\'*1024*1024) or time.sleep(0.1) for _ in range(500)]\\""]}]'"""
        ],
        "heal_cmds": [
            """kubectl rollout undo deployment/queue-worker -n training"""
        ],
        "symptoms": "queue-worker restarts rapidly with Last State: OOMKilled (Exit Code 137)."
    },
    "comp-cpu-throttling": {
        "domain": "Compute",
        "title": "CFS CPU Quota Throttling",
        "description": "Constrains order-api CPU limits to 10m while executing intensive operations.",
        "inject_cmds": [
            """kubectl patch deployment order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/cpu","value":"10m"}]'"""
        ],
        "heal_cmds": [
            """kubectl patch deployment order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/cpu","value":"500m"}]'"""
        ],
        "symptoms": "High p95 latency on order-api, Grafana CPU throttling metric > 80%."
    },
    "comp-unschedulable": {
        "domain": "Compute",
        "title": "Unschedulable Pod / Node Affinity Mismatch",
        "description": "Applies an unsatisfiable nodeSelector to order-api deployment.",
        "inject_cmds": [
            """kubectl patch deployment order-api -n training --type='json' -p='[{"op":"add","path":"/spec/template/spec/nodeSelector","value":{"topology.kubernetes.io/zone":"non-existent-zone-c"}}]'"""
        ],
        "heal_cmds": [
            """kubectl patch deployment order-api -n training --type='json' -p='[{"op":"remove","path":"/spec/template/spec/nodeSelector"}]'"""
        ],
        "symptoms": "order-api pods stuck in Pending state with FailedScheduling event."
    },
    "comp-probe-fail": {
        "domain": "Compute",
        "title": "Liveness Probe HTTP 404 Failure",
        "description": "Configures invalid liveness probe path on order-api.",
        "inject_cmds": [
            """kubectl patch deployment order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/healthz-broken-path"}]'"""
        ],
        "heal_cmds": [
            """kubectl patch deployment order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/healthz"}]'"""
        ],
        "symptoms": "order-api containers killed and restarted by kubelet every 30 seconds."
    },
    "net-policy-block": {
        "domain": "Networking",
        "title": "Restrictive NetworkPolicy / eBPF Flow Drop",
        "description": "Applies a blocking CiliumNetworkPolicy dropping traffic between frontend and order-api.",
        "inject_cmds": [
            """cat << 'EOF' | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: deny-frontend-to-api
  namespace: training
spec:
  endpointSelector:
    matchLabels:
      app: order-api
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: nonexistent-app
EOF"""
        ],
        "heal_cmds": [
            """kubectl delete ciliumnetworkpolicy deny-frontend-to-api -n training --ignore-not-found"""
        ],
        "symptoms": "Frontend displays 504 Gateway Timeout; Hubble UI shows DROPPED packets."
    },
    "net-port-mismatch": {
        "domain": "Networking",
        "title": "Service TargetPort Misconfiguration",
        "description": "Changes order-api service targetPort from 8080 to 9090.",
        "inject_cmds": [
            """kubectl patch svc order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/ports/0/targetPort","value":9090}]'"""
        ],
        "heal_cmds": [
            """kubectl patch svc order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/ports/0/targetPort","value":8080}]'"""
        ],
        "symptoms": "Pods are Running, DNS resolves, but curl to Service IP returns Connection Refused."
    },
    "net-service-endpoint": {
        "domain": "Networking",
        "title": "Service Selector Label Mismatch",
        "description": "Changes order-api service selector to match nothing.",
        "inject_cmds": [
            """kubectl patch svc order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/selector/app","value":"order-api-wrong-label"}]'"""
        ],
        "heal_cmds": [
            """kubectl patch svc order-api -n training --type='json' -p='[{"op":"replace","path":"/spec/selector/app","value":"order-api"}]'"""
        ],
        "symptoms": "Service has empty Endpoints list (`kubectl get ep order-api -n training`)."
    },
    "stor-pvc-pending": {
        "domain": "Storage",
        "title": "Unsatisfied StorageClass / Pending PVC",
        "description": "Deploys a test StatefulSet requesting a non-existent StorageClass.",
        "inject_cmds": [
            """cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: drill-pending-pvc
  namespace: training
spec:
  accessModes: [ "ReadWriteOnce" ]
  storageClassName: non-existent-nvme-sc
  resources:
    requests:
      storage: 5Gi
EOF"""
        ],
        "heal_cmds": [
            """kubectl delete pvc drill-pending-pvc -n training --ignore-not-found"""
        ],
        "symptoms": "PVC remains in Pending state; events show `StorageClass not found`."
    }
}





def list_drills():
    print(f"\n{BOLD}{BLUE}======================================================================{RESET}")
    print(f"{BOLD}{BLUE}          KUBERNETES TROUBLESHOOTING DRILL CATALOG                    {RESET}")
    print(f"{BOLD}{BLUE}======================================================================{RESET}\n")
    print(f"{BOLD}{'DOMAIN':<14} {'SCENARIO ID':<24} {'NAME'}{RESET}")
    print(f"{'-'*70}")
    for sc_id, data in SCENARIOS.items():
        domain_color = YELLOW if data["domain"] == "Compute" else (GREEN if data["domain"] == "Networking" else BLUE)
        print(f"{domain_color}{data['domain']:<14}{RESET} {BOLD}{sc_id:<24}{RESET} {data['title']}")
        print(f"               {RED}Symptoms:{RESET} {data['symptoms']}\n")
    print(f"Usage:")
    print(f"  {BOLD}make drill-inject SCENARIO=<id>{RESET}   -> Inject defect")
    print(f"  {BOLD}make drill-verify SCENARIO=<id>{RESET}   -> Observe symptoms")
    print(f"  {BOLD}make drill-heal SCENARIO=<id>{RESET}     -> Restore healthy state\n")


def inject_drill(sc_id: str):
    if sc_id not in SCENARIOS:
        print(f"{RED}Error: Unknown scenario ID '{sc_id}'. Run --list for options.{RESET}")
        sys.exit(1)
    scenario = SCENARIOS[sc_id]
    print(f"\n{BOLD}{YELLOW}>>> Injecting Failure Scenario: {sc_id} ({scenario['title']}){RESET}")
    for cmd in scenario["inject_cmds"]:
        res = run_cmd(cmd)
        if res.returncode != 0:
            print(f"{YELLOW}Warning executing injection: {res.stderr.strip()}{RESET}")
    print(f"{GREEN}✓ Scenario '{sc_id}' successfully injected!{RESET}")
    print(f"{BOLD}Expected Symptoms:{RESET} {scenario['symptoms']}")
    print(f"Refer to diagnostic runbook in: {BOLD}docs/troubleshooting-drills/{RESET}\n")


def heal_drill(sc_id: str):
    if sc_id == "all":
        print(f"\n{BOLD}{GREEN}>>> Healing all drill scenarios...{RESET}")
        for s_id in SCENARIOS:
            heal_drill(s_id)
        return

    if sc_id not in SCENARIOS:
        print(f"{RED}Error: Unknown scenario ID '{sc_id}'.{RESET}")
        sys.exit(1)
    scenario = SCENARIOS[sc_id]
    print(f"{BLUE}Healing Scenario: {sc_id}...{RESET}")
    for cmd in scenario["heal_cmds"]:
        run_cmd(cmd)
    print(f"{GREEN}✓ Scenario '{sc_id}' healed.{RESET}")


def verify_drill(sc_id: str):
    if sc_id not in SCENARIOS:
        print(f"{RED}Error: Unknown scenario ID '{sc_id}'.{RESET}")
        sys.exit(1)
    scenario = SCENARIOS[sc_id]
    print(f"\n{BOLD}Diagnostic Status for Scenario: {sc_id}{RESET}")
    print(f"Symptoms to look for: {scenario['symptoms']}\n")
    print(f"{BOLD}Active Pods in 'training' namespace:{RESET}")
    res = run_cmd("kubectl get pods -n training -o wide")
    print(res.stdout if res.stdout else res.stderr)
    print(f"\n{BOLD}Recent Events in 'training' namespace:{RESET}")
    events_res = run_cmd("kubectl get events -n training --sort-by=.metadata.creationTimestamp | tail -n 10")
    print(events_res.stdout if events_res.stdout else events_res.stderr)


def main():
    parser = argparse.ArgumentParser(description="Kubernetes Troubleshooting Drill Engine")
    parser.add_argument("--list", action="store_true", help="List all available drill scenarios")
    parser.add_argument("--inject", type=str, help="Scenario ID to inject")
    parser.add_argument("--heal", type=str, help="Scenario ID to heal (or 'all')")
    parser.add_argument("--verify", type=str, help="Verify symptoms of a scenario")

    args = parser.parse_args()

    if args.list or len(sys.argv) == 1:
        list_drills()
    elif args.inject:
        inject_drill(args.inject)
    elif args.heal:
        heal_drill(args.heal)
    elif args.verify:
        verify_drill(args.verify)


if __name__ == "__main__":
    main()
