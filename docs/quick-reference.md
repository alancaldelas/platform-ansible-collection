# Quick Reference Guide

Fast reference for common tasks with the `alancaldelas.kubernetes_baremetal` collection.

## Table of Contents

- [Quick Start Playbooks](#quick-start-playbooks)
- [Common Variables](#common-variables)
- [Useful Commands](#useful-commands)
- [Role Usage](#role-usage)
- [Debugging](#debugging)

## Quick Start Playbooks

### Minimal Kubernetes Deployment

```yaml
---
- name: Deploy Kubernetes
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
```

### Production Kubernetes Deployment

```yaml
---
- name: Deploy Production Kubernetes
  hosts: production_k8s
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_cluster_name: production
    k8s_container_runtime: containerd
    k8s_min_cpu_cores: 4
    k8s_min_memory_mb: 8192
```

### Runtime Only

```yaml
---
- name: Install Container Runtime
  hosts: all
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.runtime
  vars:
    container_runtime: containerd
    container_runtime_version: "1.7.2"
```

## Common Variables

### Container Runtime

| Variable | Default | Options |
|----------|---------|---------|
| `container_runtime` | `containerd` | `containerd`, `crio`, `docker`, `podman` |
| `container_runtime_version` | `1.7.2` | Any version |
| `containerd_build_method` | `binary` | `binary`, `source` |

### Kubernetes

| Variable | Default | Options |
|----------|---------|---------|
| `kubernetes_version` | `1.28.0` | Any K8s version |
| `k8s_cluster_name` | `kubernetes` | Any string |
| `k8s_pod_subnet` | `10.244.0.0/16` | Any CIDR |
| `k8s_service_subnet` | `10.96.0.0/12` | Any CIDR |
| `k8s_container_runtime` | `containerd` | `containerd`, `crio`, `docker` |
| `k8s_manage_container_runtime` | `true` | `true`, `false` |

### System Requirements

| Variable | Default | Purpose |
|----------|---------|---------|
| `k8s_min_cpu_cores` | `2` | Minimum CPU cores |
| `k8s_min_memory_mb` | `2048` | Minimum RAM in MB |
| `k8s_min_disk_space_gb` | `20` | Minimum disk space |

## Useful Commands

### Ansible Commands

```bash
# Install collection
ansible-galaxy collection install alancaldelas.kubernetes_baremetal

# Run playbook
ansible-playbook -i inventory deploy.yml

# Run with verbose output
ansible-playbook -i inventory deploy.yml -vvv

# Run specific role
ansible-playbook -i inventory deploy.yml --tags=runtime

# Check mode (dry run)
ansible-playbook -i inventory deploy.yml --check

# Ask for sudo password
ansible-playbook -i inventory deploy.yml -K
```

### CNI Plugin Installation (Required Post-Deployment)

**After Ansible deployment, nodes will be NotReady until you install a CNI plugin.**

Popular options:
- [Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/)
- [Flannel](https://github.com/flannel-io/flannel)
- [Cilium](https://docs.cilium.io/en/stable/gettingstarted/k8s-install-default/)

Follow the official installation guide for your chosen CNI.

### Kubernetes Commands

```bash
# Check cluster status
kubectl get nodes
kubectl get pods -A
kubectl cluster-info

# Check system pods
kubectl get pods -n kube-system

# Check node details
kubectl describe node <node-name>

# View logs
kubectl logs -n kube-system <pod-name>

# Check component health
kubectl get componentstatuses

# View events
kubectl get events --all-namespaces

# Get kubectl config
export KUBECONFIG=/etc/kubernetes/admin.conf
```

### Container Runtime Commands

**containerd:**
```bash
# Check status
systemctl status containerd

# View logs
journalctl -u containerd -f

# List images
crictl images

# List containers
crictl ps

# Pull image
crictl pull registry.k8s.io/pause:3.9
```

**CRI-O:**
```bash
# Check status
systemctl status crio

# View logs
journalctl -u crio -f

# List images
crictl images

# List containers
crictl ps
```

### System Commands

```bash
# Check swap
swapon -s

# Check kernel modules
lsmod | grep br_netfilter
lsmod | grep overlay

# Check sysctl
sysctl net.bridge.bridge-nf-call-iptables
sysctl net.ipv4.ip_forward

# Check kubelet
systemctl status kubelet
journalctl -u kubelet -f

# Check ports
netstat -tuln | grep -E "6443|10250|10251|10252"
```

## Role Usage

### Runtime Role

**Purpose:** Install and configure container runtimes

**Example:**
```yaml
- role: alancaldelas.kubernetes_baremetal.runtime
  vars:
    container_runtime: containerd
    container_runtime_version: "1.7.2"
    containerd_build_method: binary
```

**Common vars:**
- `container_runtime`: Runtime to install
- `container_runtime_version`: Version to install
- `container_registries`: List of registries
- `container_storage_path`: Storage location

### k8s Role

**Purpose:** Deploy Kubernetes cluster

**Example:**
```yaml
- role: alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_cluster_name: production
```

**Common vars:**
- `kubernetes_version`: K8s version
- `k8s_cluster_name`: Cluster name
- CNI plugins must be installed manually post-deployment
- `k8s_manage_container_runtime`: Auto-install runtime

## Debugging

### Increase Verbosity

```bash
# Basic verbosity
ansible-playbook deploy.yml -v

# More verbosity
ansible-playbook deploy.yml -vv

# Maximum verbosity
ansible-playbook deploy.yml -vvv
```

### Common Issues Quick Fixes

**SSH connection timeout:**
```bash
# Test SSH
ssh user@target-node

# Copy SSH key
ssh-copy-id user@target-node
```

**Permission denied:**
```bash
# Test sudo
ssh user@target-node 'sudo whoami'

# Add user to sudo group
sudo usermod -aG sudo username
```

**Swap enabled:**
```bash
# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

**Container runtime not running:**
```bash
# Start containerd
sudo systemctl start containerd
sudo systemctl enable containerd

# Check status
sudo systemctl status containerd
```

**kubeadm init fails:**
```bash
# Reset and retry
sudo kubeadm reset -f
ansible-playbook deploy.yml
```

**Pods pending:**
```bash
# Check CNI
kubectl get pods -n kube-system | grep -E "calico|flannel|cilium"

# Describe pod
kubectl describe pod <pod-name>
```

### Log Locations

```bash
# Ansible logs
# (shown in terminal output)

# Container runtime logs
journalctl -u containerd -f
journalctl -u crio -f

# Kubelet logs
journalctl -u kubelet -f

# Kubernetes component logs
kubectl logs -n kube-system <pod-name>

# System logs
/var/log/syslog
/var/log/messages
```

## Quick Troubleshooting Decision Tree

```
Problem?
├─ Can't connect to nodes
│  └─ Check: SSH access, firewall, network
├─ Container runtime fails
│  └─ Check: Service status, config, logs
├─ kubeadm init fails
│  ├─ Swap enabled? → Disable swap
│  ├─ Port in use? → kubeadm reset
│  └─ Runtime not running? → Start runtime
├─ Pods pending
│  ├─ CNI not ready? → Wait or redeploy CNI
│  ├─ Resources? → Check node resources
│  └─ Image pull? → Check registry access
└─ kubectl not working
   ├─ Not installed? → Check PATH
   └─ Connection refused? → Set KUBECONFIG
```

## Environment-Specific Configs

### Development

```yaml
k8s_min_cpu_cores: 1
k8s_min_memory_mb: 1024
k8s_selinux_state: permissive
k8s_disable_firewall: true
# CNI must be installed manually - flannel
```

### Staging

```yaml
k8s_min_cpu_cores: 2
k8s_min_memory_mb: 4096
k8s_selinux_state: permissive
k8s_check_network_connectivity: true
# CNI must be installed manually - calico
```

### Production

```yaml
k8s_min_cpu_cores: 4
k8s_min_memory_mb: 8192
k8s_selinux_state: enforcing
k8s_disable_firewall: false
k8s_check_network_connectivity: true
# CNI must be installed manually - calico
container_log_max_size: "100Mi"
container_log_max_files: 10
```

## Inventory Examples

### Simple Inventory

```ini
[k8s_nodes]
192.168.1.100

[all:vars]
ansible_user=ubuntu
ansible_become=yes
```

### Grouped Inventory

```ini
[k8s_dev]
dev-k8s.example.com

[k8s_prod]
prod-k8s.example.com

[k8s_dev:vars]
k8s_cluster_name=development
k8s_min_cpu_cores=1

[k8s_prod:vars]
k8s_cluster_name=production
k8s_min_cpu_cores=4
k8s_min_memory_mb=8192
```

## File Locations Reference

### Kubernetes

```
/etc/kubernetes/           # Kubernetes configs
/etc/kubernetes/admin.conf # kubectl config
/var/lib/kubelet/         # kubelet data
/var/lib/etcd/            # etcd data
/var/log/pods/            # Pod logs
```

### Container Runtime

**containerd:**
```
/etc/containerd/config.toml   # Config
/var/lib/containerd/          # Data
/run/containerd/              # Runtime
```

**CRI-O:**
```
/etc/crio/crio.conf          # Config
/var/lib/containers/         # Data
/run/crio/                   # Runtime
```

## Port Reference

| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH |
| 6443 | TCP | Kubernetes API |
| 2379-2380 | TCP | etcd |
| 10250 | TCP | Kubelet API |
| 10251 | TCP | kube-scheduler |
| 10252 | TCP | kube-controller-manager |
| 30000-32767 | TCP | NodePort Services |

## Version Compatibility

| Kubernetes | Container Runtime | CNI Plugin |
|------------|------------------|------------|
| 1.28.x | containerd 1.7+ | Any |
| 1.28.x | CRI-O 1.28+ | Any |
| 1.27.x | containerd 1.6+ | Any |
| 1.27.x | CRI-O 1.27+ | Any |

## Getting Help

**Documentation:**
- [Getting Started](getting-started.md)
- [Configuration Reference](configuration-reference.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Architecture Overview](architecture.md)
- [Production Deployment](production-deployment.md)

**External Resources:**
- [Kubernetes Docs](https://kubernetes.io/docs/)
- [Ansible Docs](https://docs.ansible.com/)
- [containerd](https://containerd.io/)
- [CRI-O](https://cri-o.io/)
