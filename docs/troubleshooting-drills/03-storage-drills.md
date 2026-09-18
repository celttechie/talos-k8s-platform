# Domain 3: Storage, CSI & Volume Troubleshooting Drills

This document contains step-by-step diagnostic runbooks for Kubernetes PersistentVolumeClaims (PVC), Longhorn dynamic volume provisioning, ReadWriteOnce locks, and disk pressure.

---

## Drill: `stor-pvc-pending` (Unsatisfied Dynamic PVC Provisioning)

### Injected Failure
The `postgres-db` StatefulSet requests a StorageClass (`storageClassName: fast-nvme-ssd`) that does not exist in the cluster, or requests an unavailable access mode.

### Step-by-Step Diagnostic Walkthrough

1. **Detect:**
   - The database pod is stuck in `Pending` or `ContainerCreating`.
   ```bash
   kubectl get pods -n training -l app=postgres-db
   # Output: postgres-db-0   0/1   Pending   0   12m
   ```

2. **Inspect PVC Status:**
   ```bash
   kubectl get pvc -n training
   # Output: data-postgres-db-0   Pending   fast-nvme-ssd   10m
   ```

3. **Check PVC Events:**
   ```bash
   kubectl describe pvc -n training data-postgres-db-0
   ```
   ```
   Warning  ProvisioningFailed  persistentvolume-controller  storageclass.storage.k8s.io "fast-nvme-ssd" not found
   ```

4. **Remediate:**
   - Verify available storage classes with `kubectl get storageclass`.
   - Update the PVC / volumeClaimTemplate to use `longhorn` (or default SC).
   - Heal:
     ```bash
     make drill-heal SCENARIO=stor-pvc-pending
     ```

---

## Drill: `stor-multi-attach` (RWO Volume Exclusivity Lock)

### Injected Failure
A ReadWriteOnce (RWO) Longhorn PersistentVolume is already attached and mounted to `talos-worker-01`, but a new replica pod is scheduled onto `talos-worker-02` attempting to mount the same underlying volume.

### Step-by-Step Diagnostic Walkthrough

1. **Detect:**
   - New pod is stuck in `ContainerCreating`.
2. **Inspect Events:**
   ```bash
   kubectl describe pod -n training <pod-name>
   ```
   ```
   Warning  FailedAttachVolume  attachdetach-controller  Multi-Attach error for volume "pvc-8789ad-..." Volume is already exclusively attached to one node and can't be attached to another
   ```
3. **Inspect Volume in Longhorn:**
   - Check Longhorn UI or query Longhorn custom resources:
     ```bash
     kubectl get volumes.longhorn.io -n longhorn-system
     ```
4. **Remediate:**
   - Ensure the older pod is properly terminated or enforce Pod Anti-Affinity / single-replica scheduling for RWO workloads.
   - Heal:
     ```bash
     make drill-heal SCENARIO=stor-multi-attach
     ```

---

## Drill: `stor-longhorn-degraded` (Replica Failure & Degraded Volume)

### Injected Failure
One worker node's secondary storage disk is detached or simulated offline, causing Longhorn dynamic volumes with replication factor 2 to drop to a single active replica (`Degraded`).

### Step-by-Step Diagnostic Walkthrough

1. **Detect via Grafana / Longhorn Dashboard:**
   - Alert: `LonghornVolumeDegraded` or `LonghornNodeStorageDown`.
   - Grafana Longhorn dashboard shows 1/2 replicas healthy.

2. **Inspect Longhorn Custom Resources:**
   ```bash
   kubectl get volumes.longhorn.io -n longhorn-system
   # Output: pvc-xyz...   Degraded   2   1
   kubectl get replicas.longhorn.io -n longhorn-system
   ```

3. **Inspect Talos Disk Health:**
   ```bash
   talosctl disks -n <worker-ip>
   talosctl dmesg -n <worker-ip> | grep -E "sd|vd"
   ```

4. **Remediate:**
   - Restore node/disk connectivity; observe Longhorn automatically triggering rebuild and sync of the replica back to `Healthy` ($2/2$).
   - Heal:
     ```bash
     make drill-heal SCENARIO=stor-longhorn-degraded
     ```
