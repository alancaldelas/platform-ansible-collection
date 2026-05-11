# k8s_upgrade Role

This Ansible role performs safe, gated in-place minor version upgrades of single-node kubeadm Kubernetes clusters. It enforces pre-flight validation, a mandatory etcd snapshot, and a strictly ordered upgrade sequence.

## Overview

The role is structured into three phases that run in strict order:

| Phase | Tag | Description | Mutates cluster? |
|-------|-----|-------------|------------------|
| 1. Pre-flight | `preflight` | Version checks, cluster health, deprecated APIs, flag audit | No (read-only) |
| 2. Snapshot | `snapshot` | etcd snapshot + PKI archive | No (backup only) |
| 3. Upgrade | `upgrade` | kubeadm upgrade apply, kubelet/kubectl update, verification | Yes |

A failure in any pre-flight check halts the play before any state changes are made to the cluster.

## Requirements

- Ansible 2.14+
- Single-node kubeadm cluster currently running the **source** minor version (`k8s_upgrade_from`)
- SSH + sudo access to the control plane node
- Internet access to `pkgs.k8s.io` for the target version package repository
- If `k8s_upgrade_use_pluto: true` (default): internet access to download the Pluto binary from GitHub

### Supported OS

- Ubuntu 22.04 (Jammy), 24.04 (Noble)
- RHEL/CentOS 8 and 9

## Role Variables

### Required

All three must be set explicitly — the role asserts they are non-empty at startup.

```yaml
k8s_upgrade_from: "1.33"              # Current cluster minor version
k8s_upgrade_to: "1.34"               # Target minor version
k8s_upgrade_target_version: "1.34.0" # Full patch version for kubeadm apply
```

Only single minor-version steps are permitted (e.g. `1.33` → `1.34`). Skipping minor versions is blocked by an assertion.

### Deprecated API Detection

```yaml
# true (default): downloads Pluto and runs it against the live cluster.
# false: uses the hardcoded removal map in vars/removed_apis_<from>_<to>.yml.
#        Use this for air-gapped environments.
k8s_upgrade_use_pluto: true
k8s_upgrade_pluto_version: "5.21.0"
k8s_upgrade_pluto_install_dir: "/usr/local/bin"
```

### Snapshot Configuration

```yaml
# Directory on the control plane node where snapshots are stored.
k8s_upgrade_snapshot_dir: "/var/lib/etcd-backups"

# Set to true to also copy snapshots to the Ansible controller.
k8s_upgrade_fetch_snapshot: false
k8s_upgrade_fetch_snapshot_dest: "{{ playbook_dir }}/backups"

# How etcdctl is invoked:
#   pod  - exec into the etcd static pod (default; no etcdctl on host required)
#   host - call etcdctl directly on the host (requires etcdctl installed)
k8s_upgrade_etcdctl_method: "pod"
```

### etcd TLS Paths (kubeadm defaults)

```yaml
k8s_upgrade_etcd_cacert: "/etc/kubernetes/pki/etcd/ca.crt"
k8s_upgrade_etcd_cert: "/etc/kubernetes/pki/etcd/peer.crt"
k8s_upgrade_etcd_key: "/etc/kubernetes/pki/etcd/peer.key"
k8s_upgrade_etcd_endpoints: "https://127.0.0.1:2379"
```

### Certificate Warning Threshold

```yaml
# Warn if certificates expire within this many days. Expired certs block the upgrade entirely.
k8s_upgrade_cert_warn_days: 30
```

### Drain Behaviour

```yaml
# false (default): skip drain/uncordon — appropriate for single-node clusters
#   where draining evicts system pods and causes unnecessary disruption.
# true: cordon -> drain -> upgrade -> uncordon
k8s_upgrade_drain_node: false
k8s_upgrade_drain_timeout: "300s"
k8s_upgrade_drain_grace_period: 30
```

## Pre-flight Checks

The pre-flight phase is entirely read-only and safe to run independently at any time:

```bash
ansible-playbook -i inventory playbooks/k8s-upgrade-1.33-to-1.34.yml --tags preflight
```

### 1. Version Enforcement (`preflight_version`)

- Asserts `k8s_upgrade_from` and `k8s_upgrade_to` differ by exactly one minor version
- Asserts `k8s_upgrade_target_version` begins with `k8s_upgrade_to`
- Queries the live cluster and asserts the server version matches `k8s_upgrade_from`

### 2. Cluster Health (`preflight_health`)

- etcd endpoint health (via pod exec or host etcdctl)
- All nodes in `Ready` state
- Failed/Unknown pods (warns, does not block)
- Certificate expiry (warns if expiring soon, blocks if already expired)
- Disk space available for the snapshot (requires 2x etcd data directory size)

### 3. Deprecated API Detection (`preflight_apis`)

- **Pluto mode** (`k8s_upgrade_use_pluto: true`): downloads [Pluto](https://github.com/FairwindsOps/pluto) and scans all resources in the live cluster against the target version. Fails with a list of affected resources if any deprecated or removed APIs are in use.
- **Map mode** (`k8s_upgrade_use_pluto: false`): queries each removed API endpoint directly via `kubectl --raw` using the hardcoded list in `vars/removed_apis_<from>_<to>.yml`. No binary download required — suitable for air-gapped environments.

### 4. kube-apiserver Flag Audit (`preflight_flags`)

- Reads `/etc/kubernetes/manifests/kube-apiserver.yaml`
- Checks for flags removed in the target version (from `vars/removed_flags_<from>_<to>.yml`)
- Checks for feature gates that graduated to GA and were removed from the binary (passing these in `--feature-gates` causes the apiserver to refuse to start)

## Snapshot Phase

Two files are written to `k8s_upgrade_snapshot_dir` on the control plane node:

- `etcd-snapshot-<timestamp>.db` — etcd data snapshot (integrity verified after creation)
- `kubernetes-pki-<timestamp>.tar.gz` — archive of `/etc/kubernetes`

The upgrade **will not proceed** if the snapshot fails or the snapshot file is missing or zero-length.

Set `k8s_upgrade_fetch_snapshot: true` to additionally pull both files to the Ansible controller.

## Upgrade Phase

Follows the kubeadm upgrade documentation order:

1. Add the target version package repository (`pkgs.k8s.io`)
2. Upgrade `kubeadm` to the target version (with hold/unhold management on Debian)
3. Run `kubeadm upgrade plan` (informational, shown in output)
4. Run `kubeadm upgrade apply`
5. Optional: cordon + drain (if `k8s_upgrade_drain_node: true`)
6. Upgrade `kubelet` and `kubectl`
7. `daemon-reload` + restart kubelet
8. Optional: uncordon
9. Wait for node to return to `Ready` (polls up to 4 minutes)
10. Assert server version matches target, display final node state

## Vars Files

Per-version-hop data files in `vars/`:

| File | Purpose |
|------|---------|
| `removed_apis_1.33_1.34.yml` | API groups removed in the 1.33 → 1.34 hop |
| `removed_flags_1.33_1.34.yml` | kube-apiserver flags and feature gates removed in 1.33 → 1.34 |

To support a new upgrade hop (e.g. 1.34 → 1.35), create corresponding `removed_apis_1.34_1.35.yml` and `removed_flags_1.34_1.35.yml` files following the format in the existing files.

## Example Playbooks

### Full Upgrade (all phases)

```yaml
---
- name: "Upgrade single-node Kubernetes cluster: 1.33 -> 1.34"
  hosts: k8s_master
  become: true
  roles:
    - alancaldelas.kubernetes_baremetal.k8s_upgrade
  vars:
    k8s_upgrade_from: "1.33"
    k8s_upgrade_to: "1.34"
    k8s_upgrade_target_version: "1.34.0"
```

### Air-Gapped Upgrade (no Pluto download)

```yaml
---
- name: "Upgrade single-node Kubernetes cluster: 1.33 -> 1.34 (air-gapped)"
  hosts: k8s_master
  become: true
  roles:
    - alancaldelas.kubernetes_baremetal.k8s_upgrade
  vars:
    k8s_upgrade_from: "1.33"
    k8s_upgrade_to: "1.34"
    k8s_upgrade_target_version: "1.34.0"
    k8s_upgrade_use_pluto: false  # Uses hardcoded API removal map instead
```

### Fetch Snapshot to Controller

```yaml
---
- name: "Upgrade with snapshot copied to controller"
  hosts: k8s_master
  become: true
  roles:
    - alancaldelas.kubernetes_baremetal.k8s_upgrade
  vars:
    k8s_upgrade_from: "1.33"
    k8s_upgrade_to: "1.34"
    k8s_upgrade_target_version: "1.34.0"
    k8s_upgrade_fetch_snapshot: true
    k8s_upgrade_fetch_snapshot_dest: "/opt/backups/k8s"
```

## Running Individual Phases

```bash
# Pre-flight only (read-only, safe at any time)
ansible-playbook -i inventory playbooks/k8s-upgrade-1.33-to-1.34.yml --tags preflight

# Snapshot only
ansible-playbook -i inventory playbooks/k8s-upgrade-1.33-to-1.34.yml --tags snapshot

# Full run (all phases)
ansible-playbook -i inventory playbooks/k8s-upgrade-1.33-to-1.34.yml
```

## Inventory

```ini
[k8s_master]
my-node ansible_host=192.168.1.100 ansible_user=ubuntu

[k8s_master:vars]
ansible_become=yes
```

## File Structure

```
k8s_upgrade/
├── defaults/main.yml                      # All default variables
├── meta/main.yml                          # Role metadata
├── tasks/
│   ├── main.yml                           # Phase orchestration
│   ├── preflight_version.yml              # Version enforcement checks
│   ├── preflight_health.yml               # Cluster health checks
│   ├── preflight_apis.yml                 # Deprecated API detection
│   ├── preflight_flags.yml                # kube-apiserver flag audit
│   ├── snapshot.yml                       # etcd snapshot and PKI backup
│   └── upgrade_control.yml                # Control plane upgrade
└── vars/
    ├── removed_apis_1.33_1.34.yml         # Removed APIs for this hop
    └── removed_flags_1.33_1.34.yml        # Removed flags/gates for this hop
```

## Troubleshooting

### Cluster version does not match `k8s_upgrade_from`

```
Live cluster is running 1.33.x but k8s_upgrade_from is set to 1.32.
```

Correct `k8s_upgrade_from` to match the actual running cluster version, then re-run.

### Insufficient disk space for snapshot

```
Insufficient disk space for etcd snapshot at /var/lib/etcd-backups.
```

Free up space on the snapshot volume or point `k8s_upgrade_snapshot_dir` to a path on a larger partition.

### Deprecated APIs found

```
Pluto detected resources using deprecated or removed APIs...
```

Migrate the listed resources to the replacement API versions shown in the error output before re-running the upgrade.

### Expired certificates

```
One or more Kubernetes certificates are EXPIRED.
```

Run `kubeadm certs renew all` on the target node, then re-run the playbook.

### kubeadm upgrade apply fails

Check the `_kubeadm_apply` output shown in the play. Common causes:
- Container runtime not running: `systemctl status containerd`
- etcd unhealthy: verify the snapshot phase passed cleanly
- Package repo unreachable: check connectivity to `pkgs.k8s.io`

## License

MIT-0

## Author Information

Part of the `alancaldelas.kubernetes_baremetal` collection.

Created by Alan Caldelas (ajcaldelas@gmail.com)
