# Configuration Reference

Comprehensive reference for all configuration variables in the `alancaldelas.kubernetes_baremetal` collection for deploying Kubernetes on bare-metal infrastructure.

## Overview

This collection deploys single-node Kubernetes clusters using kubeadm. Configuration is split into two main areas:

- **Container Runtime Configuration**: Variables for the `runtime` role
- **Kubernetes Configuration**: Variables for the `k8s` role

## Table of Contents

- [Container Runtime Variables](#container-runtime-variables)
  - [Runtime Selection](#runtime-selection)
  - [Version Configuration](#version-configuration)
  - [Registry Configuration](#registry-configuration)
  - [Storage Configuration](#storage-configuration)
  - [Build Configuration](#build-configuration)
- [Kubernetes Variables](#kubernetes-variables)
  - [Cluster Configuration](#cluster-configuration)
  - [Network Configuration](#network-configuration)
  - [Runtime Integration](#runtime-integration)
  - [System Requirements](#system-requirements)
  - [Kernel Configuration](#kernel-configuration)
  - [Security Configuration](#security-configuration)
  - [Source Installation](#source-installation)
  - [kubeadm Configuration](#kubeadm-configuration)
- [Complete Examples](#complete-examples)
- [Variable Precedence](#variable-precedence)

---

# Container Runtime Variables

**Used By:** `runtime` role

**Purpose:** Install and configure container runtimes (containerd, CRI-O, Docker, Podman) and system prerequisites

## Runtime Selection

| Variable | Default | Description | Options |
|----------|---------|-------------|---------|
| `container_runtime` | `containerd` | Container runtime to install | `containerd`, `crio`, `docker`, `podman` |
| `container_runtime_version` | `1.7.2` | Version of the container runtime | Any valid version string |
| `containerd_build_method` | `binary` | Installation method for containerd | `binary`, `source` |
| `crio_build_method` | `binary` | Installation method for CRI-O | `binary`, `source` |

**Example:**
```yaml
container_runtime: containerd
container_runtime_version: "1.7.2"
containerd_build_method: binary
```

## Version Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `runc_version` | `1.1.9` | Version of runc to install |
| `cni_version` | `1.3.0` | Version of CNI plugins |
| `go_version` | `1.21.3` | Go version for source builds |

## Registry Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `container_registries` | `[quay.io, registry.k8s.io, docker.io]` | List of container registries (HTTPS) |
| `container_insecure_registries` | `[]` | List of insecure registries (HTTP/self-signed) |
| `container_registry_mirrors` | `[]` | Registry mirrors for improved performance |

**Example:**
```yaml
container_registries:
  - quay.io
  - registry.k8s.io
  - harbor.company.com

container_insecure_registries:
  - localhost:5000
  - dev-registry.internal:8080
```

## Storage Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `container_storage_driver` | `overlay2` | Storage driver to use |
| `container_storage_path` | `/var/lib/containers` | Container storage path |
| `container_log_max_size` | `10Mi` | Maximum log file size |
| `container_log_max_files` | `3` | Number of log files to retain |

**Example:**
```yaml
container_storage_driver: overlay2
container_storage_path: /var/lib/containers
container_log_max_size: "50Mi"
container_log_max_files: 5
```

## Build Configuration

Variables for source installation (when `containerd_build_method: source` or `crio_build_method: source`)

| Variable | Default | Description |
|----------|---------|-------------|
| `containerd_build_dir` | `/tmp/containerd-build` | Build directory for containerd |
| `crio_build_dir` | `/tmp/crio-build` | Build directory for CRI-O |
| `containerd_build_packages` | See role defaults | Debian/Ubuntu build dependencies |
| `containerd_build_packages_rhel` | See role defaults | RHEL/CentOS build dependencies |

**Example:**
```yaml
containerd_build_method: source
containerd_build_dir: /tmp/containerd-build
go_version: "1.21.4"
```

---

# Kubernetes Variables

**Used By:** `k8s` role

**Purpose:** Kubernetes cluster deployment and configuration

**Note:** This collection currently supports **single-node** deployments only.

## Cluster Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `kubernetes_version` | `1.28.0` | Kubernetes version to install |
| `k8s_cluster_name` | `kubernetes` | Name of the Kubernetes cluster |

**Example:**
```yaml
kubernetes_version: "1.28.0"
k8s_cluster_name: my-cluster
```

## Network Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `k8s_pod_subnet` | `10.244.0.0/16` | Pod network CIDR (must match your CNI plugin requirements) |
| `k8s_service_subnet` | `10.96.0.0/12` | Service network CIDR |

**Important:** CNI plugins are NOT installed by this role. After cluster initialization, you must manually install your chosen CNI plugin. Popular options include [Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/), [Flannel](https://github.com/flannel-io/flannel), and [Cilium](https://docs.cilium.io/en/stable/gettingstarted/k8s-install-default/).

**Example:**
```yaml
k8s_pod_subnet: "10.244.0.0/16"  # Must match your CNI plugin's requirements
k8s_service_subnet: "10.96.0.0/12"
```

## Runtime Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `k8s_container_runtime` | `containerd` | Container runtime for Kubernetes |
| `k8s_manage_container_runtime` | `true` | Whether to install runtime via `runtime` role |

**Example:**
```yaml
k8s_container_runtime: containerd
k8s_manage_container_runtime: true  # Auto-install runtime
```

**Note:** If set to `false`, you must manually install a container runtime before running the k8s role.

## System Requirements

These variables control validation thresholds. The role will fail if requirements aren't met.

| Variable | Default | Description |
|----------|---------|-------------|
| `k8s_min_cpu_cores` | `2` | Minimum CPU cores required |
| `k8s_min_memory_mb` | `2048` | Minimum memory in MB |
| `k8s_min_disk_space_gb` | `20` | Minimum disk space in GB |
| `k8s_min_kernel_version` | `4.15` | Minimum kernel version |
| `k8s_check_network_connectivity` | `true` | Enable network connectivity checks |

**Example:**
```yaml
# Relaxed requirements for development
k8s_min_cpu_cores: 1
k8s_min_memory_mb: 1024
k8s_min_disk_space_gb: 10
```

## Kernel Configuration

### Required Kernel Modules

| Variable | Default |
|----------|---------|
| `k8s_required_kernel_modules` | See below |

**Default Modules:**
```yaml
k8s_required_kernel_modules:
  - br_netfilter
  - overlay
  - ip_vs
  - ip_vs_rr
  - ip_vs_wrr
  - ip_vs_sh
  - nf_conntrack
```

### Kernel Parameters

| Variable | Default |
|----------|---------|
| `k8s_kernel_parameters` | See below |

**Default Parameters:**
```yaml
k8s_kernel_parameters:
  - name: net.bridge.bridge-nf-call-iptables
    value: "1"
  - name: net.bridge.bridge-nf-call-ip6tables
    value: "1"
  - name: net.ipv4.ip_forward
    value: "1"
  - name: net.ipv4.conf.all.forwarding
    value: "1"
  - name: net.ipv6.conf.all.forwarding
    value: "1"
```

## Security Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `k8s_selinux_state` | `disabled` | SELinux state |
| `k8s_disable_firewall` | `false` | Whether to disable firewall |

**SELinux Options:**
- `disabled` - Disable SELinux (recommended for simplicity)
- `permissive` - SELinux logs but doesn't enforce
- `enforcing` - SELinux enforces policies (requires configuration)
- `current` - Leave SELinux as-is

**Example:**
```yaml
k8s_selinux_state: disabled
k8s_disable_firewall: false
```

## Source Installation

Build Kubernetes from source instead of using pre-built packages.

| Variable | Default | Description |
|----------|---------|-------------|
| `k8s_install_from_source` | `false` | Build Kubernetes from source |
| `k8s_build_user` | `{{ ansible_user }}` | User for building from source |
| `k8s_repo` | `https://github.com/kubernetes/kubernetes.git` | Kubernetes repository URL |
| `k8s_branch` | `v{{ kubernetes_version }}` | Branch/tag to build from |
| `k8s_dir` | `/opt/kubernetes` | Directory for source code |

**Example:**
```yaml
k8s_install_from_source: true
kubernetes_version: "1.28.0"
k8s_build_user: "{{ ansible_user }}"
go_version: "1.21.3"
k8s_repo: "https://github.com/kubernetes/kubernetes.git"
k8s_branch: "v1.28.0"
```

## kubeadm Configuration

Advanced kubeadm and kubelet configuration.

| Variable | Default | Description |
|----------|---------|-------------|
| `k8s_kubeadm_init_extra_args` | `""` | Extra arguments for kubeadm init |
| `k8s_kubelet_extra_args` | `""` | Extra arguments for kubelet |
| `k8s_feature_gates` | `[]` | Feature gates to enable |

**Example:**
```yaml
k8s_kubeadm_init_extra_args: "--skip-phases=addon/kube-proxy"
k8s_kubelet_extra_args: "--max-pods=200"
k8s_feature_gates:
  - "EphemeralContainers=true"
  - "HPAScaleToZero=true"
```

---

# Complete Examples

## Development Environment

Minimal configuration for development/testing:

```yaml
---
# Runtime
container_runtime: containerd
container_runtime_version: "1.7.2"

# Kubernetes
kubernetes_version: "1.28.0"
k8s_cluster_name: dev-cluster
# CNI must be installed manually post-deployment - flannel

# Relaxed requirements for dev
k8s_min_cpu_cores: 1
k8s_min_memory_mb: 1024
k8s_selinux_state: permissive
k8s_disable_firewall: true
```

## Production Environment

Production-grade configuration:

```yaml
---
# Runtime
container_runtime: containerd
container_runtime_version: "1.7.2"
containerd_build_method: binary

container_registries:
  - registry.k8s.io
  - quay.io
  - company-registry.com

container_storage_path: /opt/containerd/storage
container_log_max_size: "50Mi"
container_log_max_files: 5

# Kubernetes
kubernetes_version: "1.28.0"
k8s_cluster_name: production
k8s_pod_subnet: "10.244.0.0/16"
k8s_service_subnet: "10.96.0.0/12"
# CNI must be installed manually post-deployment - calico

# Container runtime integration
k8s_container_runtime: containerd
k8s_manage_container_runtime: true

# Strict requirements
k8s_min_cpu_cores: 4
k8s_min_memory_mb: 8192
k8s_check_network_connectivity: true
```

## CRI-O with Cilium

Using CRI-O runtime with Cilium CNI:

```yaml
---
# Runtime
container_runtime: crio
container_runtime_version: "1.28.0"
crio_build_method: binary

# Kubernetes
kubernetes_version: "1.28.0"
k8s_cluster_name: crio-cluster
k8s_container_runtime: crio
# CNI must be installed manually post-deployment - cilium
```

## Custom Network Configuration

Non-standard network CIDRs:

```yaml
---
kubernetes_version: "1.28.0"
k8s_cluster_name: custom-network
k8s_pod_subnet: "192.168.0.0/16"
k8s_service_subnet: "10.100.0.0/16"
# CNI must be installed manually post-deployment - flannel
```

## Source Build

Build Kubernetes from source:

```yaml
---
# Runtime (still use binary)
container_runtime: containerd

# Kubernetes from source
k8s_install_from_source: true
kubernetes_version: "1.28.0"
k8s_build_user: "{{ ansible_user }}"
go_version: "1.21.3"
k8s_repo: "https://github.com/kubernetes/kubernetes.git"
k8s_branch: "v1.28.0"
k8s_dir: "/opt/kubernetes"
```

---

# Variable Precedence

Ansible variables can be set at multiple levels. From lowest to highest precedence:

1. **Role defaults** (`roles/*/defaults/main.yml`)
2. **Inventory variables** (`group_vars/`, `host_vars/`)
3. **Playbook variables** (`vars:` section)
4. **Extra variables** (`-e` or `--extra-vars` on command line)

**Best Practice:**
- Set defaults in inventory for consistency
- Override specific values in playbooks for different scenarios
- Use extra-vars for runtime overrides (e.g., version changes)

**Example:**

```bash
# Override Kubernetes version at runtime
ansible-playbook deploy.yml -e "kubernetes_version=1.29.0"

# Override multiple variables
ansible-playbook deploy.yml \
  -e "kubernetes_version=1.29.0" \
  -e "k8s_pod_subnet=10.244.0.0/16"
```

---

# Environment-Specific Variables

## Development

```yaml
# Minimal resources
k8s_min_cpu_cores: 1
k8s_min_memory_mb: 1024
k8s_min_disk_space_gb: 10

# Relaxed security
k8s_selinux_state: permissive
k8s_disable_firewall: true

# Fast deployment
containerd_build_method: binary
k8s_check_network_connectivity: false
```

## Staging

```yaml
# Production-like resources
k8s_min_cpu_cores: 2
k8s_min_memory_mb: 4096

# Some security
k8s_selinux_state: permissive
k8s_disable_firewall: false

# Validate network
k8s_check_network_connectivity: true
```

## Production

```yaml
# Robust resources
k8s_min_cpu_cores: 4
k8s_min_memory_mb: 8192
k8s_min_disk_space_gb: 50

# Full security
k8s_selinux_state: enforcing
k8s_disable_firewall: false

# Full validation
k8s_check_network_connectivity: true

# Production runtime
container_runtime: containerd
container_log_max_size: "100Mi"
container_log_max_files: 10
```

---

# Tips and Best Practices

## Container Runtime Selection

**For Production:**
- Use `containerd` - Industry standard, well-tested
- Binary installation for stability

**For Development:**
- `containerd` or `crio` both work well
- Binary installation for speed

**For Special Cases:**
- `docker` - If you need Docker CLI compatibility
- `podman` - If you need daemonless operation

## CNI Plugin Selection

**For Most Users:**
- `calico` - Best balance of features and performance

**For Simple Setups:**
- `flannel` - Easiest to configure

**For Advanced Networking:**
- `cilium` - eBPF-based, best performance

**For Encryption:**
- `weave` - Built-in encryption

## Version Pinning

Always pin versions in production:

```yaml
kubernetes_version: "1.28.0"  # Not "latest"
container_runtime_version: "1.7.2"
```

## Registry Configuration

Use registry mirrors for better performance:

```yaml
container_registries:
  - registry.k8s.io
  - mirror.company.com  # Internal mirror

container_registry_mirrors:
  registry.k8s.io: http://mirror.company.com/k8s
```

## System Validation

Enable all validations in production:

```yaml
k8s_check_network_connectivity: true
k8s_min_cpu_cores: 4
k8s_min_memory_mb: 8192
k8s_min_kernel_version: "4.15"
```

For more information, see:
- [Getting Started Guide](getting-started.md)
- [Architecture Overview](architecture.md)
- [Role READMEs](../roles/)
