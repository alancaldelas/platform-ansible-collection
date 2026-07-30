# Kubernetes (k8s) Role

This Ansible role deploys Kubernetes clusters on bare-metal infrastructure using kubeadm. It handles system validation, prerequisites, container runtime integration, and cluster initialization.

## Features

### System Validation
- CPU, memory, and disk space validation
- Kernel version and module checks
- Network connectivity verification
- Port availability checking
- Container runtime compatibility validation
- Swap and systemd validation

### Installation Methods
- **Binary Installation**: Install from official Kubernetes repositories (default, recommended)
- **Source Installation**: Build Kubernetes components from source

### Container Runtime Integration
- Automatic detection of existing runtimes
- Integration with the `runtime` role for installation
- Support for containerd, CRI-O, and Docker

### CNI Plugin Support
- Calico (default)
- Flannel
- Weave
- Cilium

### System Configuration
- Kernel module loading (br_netfilter, overlay, ip_vs, etc.)
- Kernel parameter tuning (IP forwarding, bridge netfilter, conntrack)
- SELinux configuration (RHEL/CentOS)
- Firewall management (optional)
- Required package installation

## Requirements

- Ansible 2.9+
- Target systems: Linux (Debian/Ubuntu, RHEL/CentOS/Fedora)
- Root or sudo access on target hosts
- Internet connectivity for downloading packages
- Minimum system requirements:
  - 2 CPU cores
  - 2GB RAM (4GB recommended)
  - 20GB disk space
  - Kernel 4.15+

## Role Variables

### Kubernetes Version
```yaml
kubernetes_version: "1.28.0"  # Kubernetes version to install
```

### System Validation Requirements
```yaml
k8s_min_cpu_cores: 2           # Minimum CPU cores
k8s_min_memory_mb: 2048        # Minimum RAM in MB
k8s_min_disk_space_gb: 20      # Minimum disk space in GB
k8s_min_kernel_version: "4.15" # Minimum kernel version

k8s_required_mount_points:     # Mount points to check for disk space
  - "/"
  - "/var"
```

### Kernel Configuration
```yaml
# Required kernel modules
k8s_required_kernel_modules:
  - br_netfilter
  - overlay
  - ip_vs
  - ip_vs_rr
  - ip_vs_wrr
  - ip_vs_sh
  - nf_conntrack

# Kernel parameters
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
  - name: net.netfilter.nf_conntrack_max
    value: "131072"
```

### Network Connectivity
```yaml
# Check connectivity to these endpoints
k8s_required_endpoints:
  - "https://registry.k8s.io"
  - "https://github.com"
  - "https://download.docker.com"

k8s_check_network_connectivity: true  # Enable/disable connectivity checks
```

### Required Ports
```yaml
k8s_required_ports:
  - 6443   # Kubernetes API server
  - 2379   # etcd server client API
  - 2380   # etcd server peer API
  - 10250  # Kubelet API
  - 10251  # kube-scheduler
  - 10252  # kube-controller-manager
  - 10255  # Read-only Kubelet API
```

### Container Runtime Integration
```yaml
k8s_container_runtime: containerd        # containerd, crio, docker
k8s_manage_container_runtime: true       # Whether to install container runtime
k8s_container_runtime_version: "1.7.2"   # Runtime version (when managed)
```

### Cluster Configuration
```yaml
k8s_cluster_name: kubernetes             # Cluster name
k8s_pod_subnet: "10.244.0.0/16"         # Pod network CIDR
k8s_service_subnet: "10.96.0.0/12"      # Service network CIDR

# Node role — controls whether this node runs kubeadm init or kubeadm join.
# master: initialises the control plane
# worker: joins an existing cluster
k8s_node_role: master
```

### Multi-Node Configuration
```yaml
# DNS name or VIP that workers use to reach the API server.
# If not set, the master's default IPv4 address is used.
# REQUIRED when k8s_ha_enabled: true.
k8s_control_plane_endpoint: ""           # e.g. "k8s-api.example.com:6443"

# Enable HA control plane mode.
# When true, kubeadm init runs with --upload-certs so additional control
# plane nodes can join with kubeadm join --control-plane.
# Requires k8s_control_plane_endpoint to be set.
k8s_ha_enabled: false

# Ansible inventory group containing the PRIMARY control plane node (ran init).
# Additional CP nodes and workers delegate token/cert generation to this group.
k8s_master_group: "k8s_masters"

# Ansible inventory group for additional control plane nodes (HA only).
k8s_cp_join_group: "k8s_control_planes"

# TTL for the bootstrap token generated on the master for workers to join.
k8s_join_token_ttl: "1h"

# Ports validated on worker nodes (subset of master port list).
k8s_worker_required_ports:
  - 10250  # Kubelet API
  - 10255  # Read-only Kubelet API
```

### Node Roles

| `k8s_node_role` | Action |
|-----------------|--------|
| `master` | Runs `kubeadm init`. Installs CNI. |
| `control_plane_join` | Joins as an additional control plane node (`kubeadm join --control-plane`). Requires `k8s_ha_enabled: true`. |
| `worker` | Joins as a worker node (`kubeadm join`). |

### CNI Plugin Selection
```yaml
k8s_cni_plugin: calico  # calico, flannel, weave, cilium
```

### kubeadm Configuration
```yaml
k8s_kubeadm_init_extra_args: ""   # Additional kubeadm init arguments
k8s_kubeadm_join_extra_args: ""   # Additional kubeadm join arguments
k8s_kubelet_extra_args: ""        # Additional kubelet arguments
k8s_feature_gates: []             # Kubernetes feature gates to enable
```

### Security Configuration (RHEL/CentOS)
```yaml
k8s_selinux_state: disabled       # disabled, permissive, enforcing, current
k8s_selinux_policy: targeted      # SELinux policy type

k8s_selinux_booleans:             # SELinux booleans for Kubernetes
  - name: container_manage_cgroup
    state: yes
  - name: virt_use_nfs
    state: yes
  - name: virt_sandbox_use_all_caps
    state: yes

k8s_disable_firewall: false       # Disable firewalld/ufw (not recommended for production)
```

### Source Installation (Advanced)
```yaml
k8s_install_from_source: false           # Build from source instead of using packages
k8s_build_user: "{{ ansible_user }}"     # User to build as
k8s_repo: "https://github.com/kubernetes/kubernetes.git"
k8s_branch: "v{{ kubernetes_version }}"
k8s_dir: "/opt/kubernetes"               # Build directory

# Go configuration for source builds
go_version: "1.21.3"
go_url: "https://golang.org/dl"
```

## Dependencies

### Role Dependencies
- `runtime` role (optional, if `k8s_manage_container_runtime: true`)

### System Dependencies
Automatically installed by the role:
- curl, wget, ca-certificates, gnupg, lsb-release
- Debian/Ubuntu: apt-transport-https, software-properties-common
- RHEL/CentOS: yum-utils, device-mapper-persistent-data, lvm2

## Example Playbooks

### Multi-Node Cluster (1 master + N workers)

```yaml
# Inventory:
#   [k8s_masters]
#   master01 ansible_host=192.168.1.10 ansible_user=ubuntu
#
#   [k8s_workers]
#   worker01 ansible_host=192.168.1.11 ansible_user=ubuntu
#   worker02 ansible_host=192.168.1.12 ansible_user=ubuntu
#
#   [k8s_cluster:children]
#   k8s_masters
#   k8s_workers
#
#   [k8s_cluster:vars]
#   ansible_become=yes

---
# Phase 1: control plane
- name: Deploy control plane
  hosts: k8s_masters
  become: true
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    k8s_node_role: master
    k8s_master_group: k8s_masters
    k8s_cni_plugin: calico

# Phase 2: workers
- name: Join workers
  hosts: k8s_workers
  become: true
  serial: 1
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    k8s_node_role: worker
    k8s_master_group: k8s_masters
    k8s_install_cni: false
```

See `playbooks/k8s-multi-node.yml` for a complete example with verification.

---

### HA Control Plane (3 control plane nodes + workers)

```yaml
# Inventory:
#   [k8s_masters]        <- primary (runs kubeadm init)
#   master01 ansible_host=192.168.1.10 ansible_user=ubuntu
#
#   [k8s_control_planes] <- additional control plane nodes
#   master02 ansible_host=192.168.1.11 ansible_user=ubuntu
#   master03 ansible_host=192.168.1.12 ansible_user=ubuntu
#
#   [k8s_workers]
#   worker01 ansible_host=192.168.1.20 ansible_user=ubuntu

---
# Phase 1: primary control plane
- name: Deploy primary control plane
  hosts: k8s_masters
  become: true
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    k8s_node_role: master
    k8s_ha_enabled: true
    k8s_master_group: k8s_masters
    k8s_control_plane_endpoint: "k8s-api.example.com:6443"
    k8s_cni_plugin: cilium

# Phase 2: additional control plane nodes (serial: 1 for etcd quorum)
- name: Join additional control plane nodes
  hosts: k8s_control_planes
  become: true
  serial: 1
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    k8s_node_role: control_plane_join
    k8s_ha_enabled: true
    k8s_master_group: k8s_masters
    k8s_control_plane_endpoint: "k8s-api.example.com:6443"
    k8s_install_cni: false

# Phase 3: workers
- name: Join workers
  hosts: k8s_workers
  become: true
  serial: 1
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    k8s_node_role: worker
    k8s_ha_enabled: true
    k8s_master_group: k8s_masters
    k8s_control_plane_endpoint: "k8s-api.example.com:6443"
    k8s_install_cni: false
```

See `playbooks/k8s-ha-control-plane.yml` for a complete example with etcd health verification.

---

### Basic Single-Node Kubernetes Cluster
```yaml
---
- name: Deploy Kubernetes cluster
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_container_runtime: containerd
    k8s_cni_plugin: calico
```

### Kubernetes with Custom Network Configuration
```yaml
---
- name: Deploy Kubernetes with custom networking
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_container_runtime: containerd
    k8s_cni_plugin: calico
    k8s_pod_subnet: "10.100.0.0/16"
    k8s_service_subnet: "10.200.0.0/16"
    k8s_cluster_name: "production-k8s"
```

### Kubernetes with CRI-O Runtime
```yaml
---
- name: Deploy Kubernetes with CRI-O
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_container_runtime: crio
    k8s_manage_container_runtime: true
    k8s_cni_plugin: cilium
```

### Multi-Role Deployment with Manual Runtime
```yaml
---
- name: Deploy complete Kubernetes stack
  hosts: k8s_nodes
  become: yes

  tasks:
    - name: Install container runtime
      include_role:
        name: alancaldelas.kubernetes_baremetal.runtime
      vars:
        container_runtime: containerd
        container_runtime_version: "1.7.2"
        containerd_build_method: binary

    - name: Deploy Kubernetes
      include_role:
        name: alancaldelas.kubernetes_baremetal.k8s
      vars:
        kubernetes_version: "1.28.0"
        k8s_manage_container_runtime: false  # Already installed above
        k8s_cni_plugin: calico
```

### Production Configuration with SELinux
```yaml
---
- name: Deploy production Kubernetes on RHEL
  hosts: production_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_container_runtime: crio
    k8s_cni_plugin: calico
    k8s_cluster_name: "prod-cluster"
    k8s_selinux_state: enforcing
    k8s_min_cpu_cores: 4
    k8s_min_memory_mb: 8192
    k8s_disable_firewall: false
```

### Skip Network Connectivity Checks (Air-Gapped)
```yaml
---
- name: Deploy Kubernetes in air-gapped environment
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_check_network_connectivity: false
    k8s_required_endpoints: []
```

## Architecture

### Task Flow

1. **System Validation** (`system_validation.yml`)
   - Validate CPU, memory, disk space
   - Check kernel version and modules
   - Test network connectivity
   - Verify port availability
   - Check container runtime compatibility
   - Validate swap is disabled
   - Configure kernel modules and parameters
   - Install required packages
   - Configure SELinux (RHEL/CentOS)

2. **Container Runtime Setup**
   - Check for existing runtime
   - Include `runtime` role if needed
   - Validate runtime is running

3. **Kubernetes Installation**
   - Add Kubernetes repository
   - Install kubelet, kubeadm, kubectl
   - Generate kubeadm configuration
   - Initialize cluster (master nodes)
   - Configure kubectl access
   - Deploy CNI plugin

### File Structure
```
k8s/
├── defaults/main.yml              # Default variables
├── handlers/main.yml              # Service restart handlers
├── tasks/
│   ├── main.yml                  # Main task orchestration
│   ├── system_validation.yml     # System validation and prerequisites
│   ├── kubernetes_install.yml    # Install from packages
│   └── kubernetes_install_source.yml  # Build from source
├── templates/
│   ├── kubeadm-config.yaml.j2    # kubeadm cluster configuration
│   └── uninstall.sh.j2           # Uninstall script
└── vars/main.yml                 # Internal variables
```

### System Validation Checks

The role performs comprehensive validation before installation:

- **Hardware**: CPU cores, RAM, disk space on required mount points
- **Kernel**: Version check, required modules availability
- **Network**: Connectivity to registries, port availability
- **Runtime**: Existing runtime detection, compatibility check
- **System**: systemd availability, swap disabled, required packages

## Advanced Usage

### Building from Source

For latest features or custom patches:

```yaml
k8s_install_from_source: true
kubernetes_version: "1.29.0"
go_version: "1.21.4"
k8s_build_user: "builder"
```

### Custom Feature Gates

Enable experimental Kubernetes features:

```yaml
k8s_feature_gates:
  - "SomeFeatureGate=true"
  - "AnotherFeature=false"
```

### Custom kubelet Arguments

Add additional kubelet configuration:

```yaml
k8s_kubelet_extra_args: "--node-ip={{ ansible_default_ipv4.address }} --max-pods=250"
```

## Post-Installation

After successful installation:

1. **Access cluster** (on master node):
   ```bash
   mkdir -p $HOME/.kube
   sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
   sudo chown $(id -u):$(id -g) $HOME/.kube/config
   ```

2. **Verify cluster**:
   ```bash
   kubectl get nodes
   kubectl get pods -A
   ```

3. **Join worker nodes** (if multi-node):
   ```bash
   # Get join command from master
   kubeadm token create --print-join-command
   ```

## Troubleshooting

### Common Issues

1. **Swap is enabled**
   - Error: "Swap is enabled. Kubernetes requires swap to be disabled"
   - Solution: Disable swap: `sudo swapoff -a && sudo sed -i '/swap/d' /etc/fstab`

2. **Port already in use**
   - Error: "Required port XXXX is already in use"
   - Solution: Identify and stop service using the port: `sudo lsof -i :XXXX`

3. **Kernel module not available**
   - Error: "Required kernel module 'XXX' is not available"
   - Solution: Update kernel or enable module in kernel config

4. **Container runtime mismatch**
   - Error: "Found existing runtime 'X' but configured for 'Y'"
   - Solution: Either uninstall existing runtime or set `k8s_manage_container_runtime: false`

5. **Network connectivity issues**
   - Error: "Cannot reach required endpoint"
   - Solution: Check firewall, proxy settings, or set `k8s_check_network_connectivity: false`

### Debug Mode

Enable verbose Ansible output:
```bash
ansible-playbook -vvv playbook.yml
```

Check system logs:
```bash
journalctl -u kubelet -f
journalctl -u containerd -f
```

## Uninstallation

An uninstall script is generated at `/root/uninstall.sh` on the target node:

```bash
sudo /root/uninstall.sh
```

This will:
- Reset kubeadm configuration
- Remove Kubernetes packages
- Clean up configuration files

## License

MIT-0

## Author Information

This role is part of the kubernetes_baremetal collection for automating Kubernetes deployments on bare-metal infrastructure.

Created by Alan Caldelas (ajcaldelas@gmail.com)

## Contributing

1. Follow Ansible best practices
2. Test on all supported OS families (Debian/Ubuntu, RHEL/CentOS/Fedora)
3. Update documentation for new features
4. Ensure backward compatibility
5. Add validation for new configuration options
