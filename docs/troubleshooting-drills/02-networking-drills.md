# Domain 2: Networking, eBPF & DNS Troubleshooting Drills

This document contains step-by-step diagnostic runbooks for Kubernetes network routing, DNS resolution, Cilium eBPF packet filtering, and Service endpoint mismatches.

---

## Drill: `net-dns-timeout` (CoreDNS Breakdown & Resolution Failure)

### Injected Failure
The microservices cannot resolve internal cluster DNS records (e.g. `order-api.training.svc.cluster.local`) or external hostnames due to an injected upstream DNS blackhole or degraded CoreDNS deployment.

### Step-by-Step Diagnostic Walkthrough

1. **Detect in Application Logs:**
   - Frontend web UI displays `502 Bad Gateway` or `Connection Error`.
   - Inspect frontend logs:
     ```bash
     kubectl logs -n training -l app=frontend --tail=20
     # Error: dial tcp: lookup order-api.training.svc.cluster.local: i/o timeout
     ```

2. **Diagnose with `kubectl exec` / Debug Pod:**
   ```bash
   kubectl exec -it -n training $(kubectl get pod -n training -l app=frontend -o jsonpath='{.items[0].metadata.name}') -- nslookup order-api.training.svc.cluster.local
   ```
   Notice that the DNS query sent to `10.96.0.10:53` times out.

3. **Check CoreDNS Health:**
   ```bash
   kubectl get pods -n kube-system -l k8s-app=kube-dns
   kubectl logs -n kube-system -l k8s-app=kube-dns
   ```

4. **Remediate:**
   - Restore healthy CoreDNS ConfigMap or pods.
   - Heal:
     ```bash
     make drill-heal SCENARIO=net-dns-timeout
     ```

---

## Drill: `net-policy-block` (CiliumNetworkPolicy Drop)

### Injected Failure
A restrictive `CiliumNetworkPolicy` or standard `NetworkPolicy` is applied to the `training` namespace, dropping egress traffic from `frontend` to `order-api`.

### Step-by-Step Diagnostic Walkthrough

1. **Detect via Hubble Flow Visualizer:**
   - Open Hubble UI (`make hubble-ui`).
   - Select namespace `training`.
   - Observe red dropped flow lines connecting `frontend` $\to$ `order-api` on TCP port 8080.

2. **Inspect via Hubble CLI:**
   ```bash
   hubble observe --namespace training --verdict DROPPED
   ```
   Output:
   ```
   training/frontend-5d8f7b886-x7kq8:49212 -> training/order-api-65db9899f-v9w2l:8080 Policy denied DROPPED (CiliumNetworkPolicy training/deny-api-traffic)
   ```

3. **Inspect Policy Resource:**
   ```bash
   kubectl get ciliumnetworkpolicies -n training
   kubectl describe ciliumnetworkpolicy -n training deny-api-traffic
   ```

4. **Remediate:**
   - Update or delete the blocking policy rule to allow egress/ingress on port 8080.
   - Heal:
     ```bash
     make drill-heal SCENARIO=net-policy-block
     ```

---

## Drill: `net-port-mismatch` (TargetPort Misconfiguration)

### Injected Failure
The `order-api` Service defines `targetPort: 9090`, while the container actually listens on port `8080`.

### Step-by-Step Diagnostic Walkthrough

1. **Symptoms:**
   - Pods are `Running` (1/1).
   - DNS resolution succeeds (`order-api.training.svc.cluster.local` $\to$ Service ClusterIP `10.96.x.x`).
   - Connection to the Service immediately returns `Connection refused` (RST packet).

2. **Inspect Service vs Container Ports:**
   ```bash
   kubectl get svc order-api -n training -o yaml | grep -A 5 ports
   kubectl get deployment order-api -n training -o yaml | grep -A 5 containerPort
   ```
   Notice that `service.spec.ports[0].targetPort` is `9090`, but `containerPort` is `8080`.

3. **Remediate:**
   - Patch the service `targetPort` to match `8080`.
   - Heal:
     ```bash
     make drill-heal SCENARIO=net-port-mismatch
     ```

---

## Drill: `net-service-endpoint` (Missing Selector / Empty Endpoints)

### Injected Failure
The `order-api` Service selector specifies `app: order-backend`, but the deployment pods are labeled with `app: order-api`.

### Step-by-Step Diagnostic Walkthrough

1. **Detect:**
   - Calling the Service IP times out or returns `No route to host`.
2. **Inspect Endpoints / EndpointSlices:**
   ```bash
   kubectl get endpoints -n training order-api
   # Output: NAME        ENDPOINTS   AGE
   #         order-api   <none>      5m
   ```
3. **Compare Selectors:**
   ```bash
   kubectl get svc order-api -n training -o jsonpath='{.spec.selector}'
   kubectl get pods -n training --show-labels
   ```
4. **Remediate:**
   - Align the service selector labels with the pod metadata labels.
   - Heal:
     ```bash
     make drill-heal SCENARIO=net-service-endpoint
     ```
