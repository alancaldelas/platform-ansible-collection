# cluster_upgrade

Orchestrates a full cluster upgrade including Kubernetes (control planes and workers) and CNI components (e.g. Cilium).

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `k8s_upgrade_node_role` | `master` | The role of the node being upgraded (`master` or `worker`). |
| `k8s_upgrade_from` | `""` | The current cluster minor version, e.g. "1.33" |
| `k8s_upgrade_to` | `""` | The target minor version, e.g. "1.34" |
| `k8s_upgrade_target_version` | `""` | The full version for kubeadm apply, e.g. "1.34.0" |
| `k8s_cni_plugin` | `cilium` | The CNI plugin being used. |
| `cilium_version` | `1.19.6` | The target Cilium version to upgrade to. |
| `k8s_upgrade_drain_worker_node` | `true` | Whether to drain worker nodes during upgrade. |

## Dependencies

- `k8s_upgrade` role for control plane upgrades.

## Example Playbook

```yaml
- hosts: all
  roles:
    - { role: cluster_upgrade }
```
