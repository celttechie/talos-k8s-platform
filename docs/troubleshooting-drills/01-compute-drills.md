# Domain 1: Compute & Scheduling Troubleshooting Drills

This document contains step-by-step diagnostic runbooks for Kubernetes compute, scheduling, resource limits, and lifecycle probe issues.

---

## Drill: `comp-oom-killed` (Out Of Memory / Exit Code 137)

### Injected Failure
The `queue-worker` background workload experiences a progressive memory leak, rapidly exceeding its container `resources.limits.memory`.

### Step-by-Step Diagnostic Walkthrough

1. **Detect via Prometheus / Grafana:**
   - Open the **Kubernetes / Compute Resources / Workload** Grafana dashboard.
   - Observe the memory usage for `queue-worker` spiking sharply to the limit line (e.g., `128Mi`) before plummeting instantly.
   - Notice the **Pod Restarts** counter incrementing.

2. **Inspect with `kubectl`:**
   ```bash
   kubectl get pods -n training -l app=queue-worker
   # Output: RESTARTS: 3 (CrashLoopBackOff or Error)
   ```

3. **Isolate Root Cause:**
   ```bash
   kubectl describe pod -n training -l app=queue-worker
   ```
   Check the `Last State` in the container details:
   ```yaml
   Last State:     Terminated
     Reason:       OOMKilled
     Exit Code:    137
   ```

4. **Remediate:**
   - Either increase the memory limit in the deployment manifest or fix the application memory leak.
   - Heal the drill:
     ```bash
     make drill-heal SCENARIO=comp-oom-killed
     ```

---

## Drill: `comp-cpu-throttling` (CFS Quota Starvation)

### Injected Failure
The `order-api` microservice is configured with an overly restrictive CPU limit (`50m` / 0.05 core) during a heavy synthetic query load.

### Step-by-Step Diagnostic Walkthrough

1. **Detect:**
   - Application p95 and p99 response times spike significantly.
   - Open Grafana **Compute Pressure** dashboard and inspect the **CPU Throttling Percentage** panel. Throttling is $> 80\%$.

2. **Inspect with `kubectl`:**
   ```bash
   kubectl top pod -n training -l app=order-api
   ```
   Note that the CPU usage is pegged at the exact configured ceiling.

3. **Remediate:**
   - Adjust `resources.limits.cpu` in `gitops/apps/training-app/base/order-api.yaml` or remove strict CPU limits in favor of appropriate `requests.cpu`.
   - Heal:
     ```bash
     make drill-heal SCENARIO=comp-cpu-throttling
     ```

---

## Drill: `comp-unschedulable` (Scheduling / Node Affinity Failure)

### Injected Failure
A critical deployment requests a node selector or node affinity rule (e.g., `topology.kubernetes.io/zone: zone-c` or `gpu=true`) that matches zero nodes in the cluster, or requests more CPU than any worker can schedule.

### Step-by-Step Diagnostic Walkthrough

1. **Detect:**
   - Pod is stuck in `Pending` state indefinitely.
   ```bash
   kubectl get pods -n training
   # Output: order-api-...   0/1   Pending   0   10m
   ```

2. **Inspect Scheduler Events:**
   ```bash
   kubectl describe pod -n training -l app=order-api
   ```
   Look at the bottom `Events:` section:
   ```
   Warning  FailedScheduling  default-scheduler  0/3 nodes are available: 1 node(s) had untolerated taint {node-role.kubernetes.io/control-plane: }, 2 node(s) didn't match Pod's node affinity/selector.
   ```

3. **Remediate:**
   - Review node labels with `kubectl get nodes --show-labels`.
   - Update the pod's `nodeSelector` / `affinity` to match actual cluster topology.
   - Heal:
     ```bash
     make drill-heal SCENARIO=comp-unschedulable
     ```

---

## Drill: `comp-probe-fail` (Liveness / Readiness Probe Breakdown)

### Injected Failure
The `order-api` deployment specifies a liveness probe path `/healthz-bad` that returns HTTP 404.

### Step-by-Step Diagnostic Walkthrough

1. **Detect:**
   - Pod starts, runs for ~30 seconds, and then restarts repeatedly.
   - `kubectl get pods -n training` shows high restart count with status `Running` $\to$ `CrashLoopBackOff`.

2. **Inspect Events:**
   ```bash
   kubectl describe pod -n training -l app=order-api
   ```
   ```
   Warning  Unhealthy  kubelet  Liveness probe failed: HTTP probe failed with statuscode: 404
   Normal   Killing    kubelet  Container order-api failed liveness probe, will be restarted
   ```

3. **Remediate:**
   - Correct the probe path to `/healthz` or the appropriate port.
   - Heal:
     ```bash
     make drill-heal SCENARIO=comp-probe-fail
     ```
