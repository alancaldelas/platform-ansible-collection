# Architecture Overview

This document provides a comprehensive overview of the `alancaldelas.kubernetes_baremetal` collection architecture, design decisions, and internal workings for deploying Kubernetes on bare-metal infrastructure.

## Overview

This collection deploys single-node Kubernetes clusters on bare-metal servers using:
- **Ansible** for orchestration
- **SSH** to connect to target nodes
- **kubeadm** for cluster initialization
- **Multiple container runtime** options (containerd, CRI-O, Docker, Podman)
- **CNI plugins** for networking (Calico, Flannel, Weave, Cilium)

## Table of Contents

- [Collection Structure](#collection-structure)
- [Deployment Model](#deployment-model)
- [Role Architecture](#role-architecture)
- [Workflow and Dependencies](#workflow-and-dependencies)
- [Design Patterns](#design-patterns)
- [Container Runtime Integration](#container-runtime-integration)
- [Extensibility](#extensibility)

## Collection Structure

```
alancaldelas.kubernetes_baremetal/
├── docs/                                 # Documentation
│   ├── architecture.md                   # This file
│   ├── configuration-reference.md        # Variable reference
│   ├── getting-started.md               # Quick start guide
│   ├── production-deployment.md         # Production guide
│   └── troubleshooting.md               # Troubleshooting
├── galaxy.yml                           # Collection metadata
├── meta/                                # Collection-level metadata
│   └── runtime.yml                      # Ansible version requirements
├── playbooks/                           # Example playbooks (optional)
├── plugins/                             # Ansible plugins (if any)
│   └── README.md
├── README.md                            # Collection README
└── roles/                               # Collection roles
    ├── k8s/                             # Kubernetes deployment
    └── runtime/                         # Container runtime
```

## Deployment Model

### Execution Architecture

The collection uses a traditional Ansible SSH-based deployment model:

```
┌──────────────────────────────────────────┐
│ Control Node (your laptop/workstation)   │
│ - Runs Ansible                           │
│ - Stores playbooks                       │
│ - Has SSH access to target nodes         │
└───────────┬──────────────────────────────┘
            │
            │ SSH Connection (Port 22)
            │ Ansible executes tasks remotely
            ↓
┌──────────────────────────────────────────┐
│ Target Node (bare-metal server)          │
│ - Runs Linux (Debian/Ubuntu/RHEL)        │
│ - Kubernetes gets installed here         │
│ - Actual cluster runs here               │
└──────────────────────────────────────────┘
```

**Key Points:**
- **Control Node**: Just needs Ansible installed - runs locally on your machine
- **Target Node**: Where all the heavy lifting happens - runs Kubernetes
- **Communication**: Standard SSH (no special protocols)
- **Approach**: Traditional configuration management

### Deployment Workflow

1. **Control Node → Target Node (SSH)**
   - Ansible connects via SSH
   - Executes tasks as root/sudo

2. **System Preparation**
   - Load kernel modules
   - Configure sysctl parameters
   - Disable swap

3. **Container Runtime Installation**
   - Install containerd/CRI-O/docker
   - Configure registries
   - Start runtime service

4. **Kubernetes Installation**
   - Install kubeadm, kubelet, kubectl
   - Initialize cluster
   - Deploy CNI plugin

5. **Result**
   - Running Kubernetes cluster on target node
   - kubectl access configured

## Role Architecture

### Two Main Roles

#### 1. runtime

**Purpose:** Install and configure container runtimes + system prerequisites

**Execution Location:** Target nodes (via SSH)

**Responsibilities:**
- **System Prerequisites:**
  - Load kernel modules (overlay, br_netfilter)
  - Configure sysctl parameters
  - Disable swap and zswap
  - Install base packages

- **Container Runtime:**
  - Install chosen runtime (containerd, CRI-O, Docker, Podman)
  - Configure registries
  - Start and enable services

**Architecture:**
```
runtime/
├── defaults/main.yml           # Default variables
├── files/
│   ├── containerd.service      # systemd unit for containerd
│   └── crio.service           # systemd unit for CRI-O
├── handlers/main.yml          # Service restart handlers
├── tasks/
│   ├── main.yml              # Orchestration
│   ├── common.yml            # System prerequisites (kernel, sysctl, swap)
│   ├── containerd.yml        # containerd installation
│   ├── crio.yml              # CRI-O installation
│   ├── docker.yml            # Docker installation
│   └── podman.yml            # Podman installation
├── templates/
│   ├── containerd-config.toml.j2  # containerd config
│   └── crio.conf.j2              # CRI-O config
└── vars/main.yml             # Internal variables
```

**Installation Methods:**
1. **Binary Installation** (default): Download pre-built binaries
2. **Source Installation**: Compile from source code

**Supported Runtimes:**
- `containerd` - Industry standard, production-ready
- `crio` - Kubernetes-native, lightweight
- `docker` - Traditional, development use
- `podman` - Daemonless, specific use cases

#### 2. k8s

**Purpose:** Deploy and configure Kubernetes clusters

**Execution Location:** Target nodes (via SSH)

**Responsibilities:**
- **System Validation:**
  - Check CPU, memory, disk requirements
  - Validate kernel version
  - Verify network connectivity
  - Check port availability

- **Runtime Management:**
  - Optionally include `runtime` role
  - Validate runtime is running

- **Kubernetes Installation:**
  - Install kubeadm, kubelet, kubectl (from packages or source)
  - Configure kubelet

- **Cluster Initialization:**
  - Run `kubeadm init` for single-node cluster
  - Configure kubectl access
  - Taint master to allow workloads

- **CNI Deployment:**
  - Deploy chosen CNI plugin

**Architecture:**
```
k8s/
├── defaults/main.yml              # Default variables
├── tasks/
│   ├── main.yml                   # Main orchestration
│   ├── system_validation.yml      # System validation and prep
│   ├── kubernetes_install.yml     # Binary installation
│   └── kubernetes_install_source.yml  # Source installation
├── templates/
│   └── kubeadm-config.yaml.j2     # kubeadm configuration
├── files/                         # CNI manifests
└── handlers/main.yml              # Service handlers
```

**Installation Methods:**
1. **Binary Installation** (default): From official Kubernetes repositories
2. **Source Installation**: Build from kubernetes/kubernetes repository

**Supported CNI Plugins:**
- `calico` - Network policies, BGP routing
- `flannel` - Simple overlay network
- `weave` - Mesh networking, encryption
- `cilium` - eBPF-based, advanced features

**Current Limitation:** Single-node deployments only

## Workflow and Dependencies

### Role Dependencies

```
k8s role
  └── Optionally includes: runtime role (if k8s_manage_container_runtime: true)
      └── The runtime role handles all system prerequisites internally
```

**Note:** The `k8s` role can optionally manage container runtime installation. If `k8s_manage_container_runtime` is `true` (default), it automatically includes the `runtime` role.

### Complete Deployment Workflow

```
┌─────────────────────────────────────────────────────┐
│ Ansible Control Node                                │
│ Connects to: Target Kubernetes Nodes (SSH)          │
└─────────────┬───────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────┐
│ ON TARGET NODES:                                     │
│                                                       │
│ 1. Container Runtime & System Setup (runtime role)  │
│    - Load kernel modules (overlay, br_netfilter)    │
│    - Configure sysctl parameters                     │
│    - Disable swap/zswap                              │
│    - Install chosen runtime (containerd/CRI-O)      │
│    - Configure registries                            │
│    - Start and enable service                        │
└─────────────┬───────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────┐
│ 2. Kubernetes Installation (k8s role)                │
│    - Validate system requirements (CPU, RAM, disk)  │
│    - Add Kubernetes repository                       │
│    - Install kubeadm, kubelet, kubectl              │
│    OR                                                │
│    - Build from source (if enabled)                  │
└─────────────┬───────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────┐
│ 3. Cluster Initialization (k8s role)                │
│    - kubeadm init (single node only)                │
│    - Note: Multi-node not currently supported       │
└────────────────┬───────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────┐
│ 4. CNI Deployment (k8s role)                        │
│    - Deploy chosen CNI (Calico/Flannel/Cilium)    │
└────────────────┬───────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────┐
│ 5. Result: Running Kubernetes Cluster              │
│    - kubectl configured                             │
│    - CNI plugin active                              │
│    - Ready to deploy workloads                      │
└────────────────────────────────────────────────────┘
```

## Design Patterns

### Idempotency

All tasks are designed to be idempotent - running the playbook multiple times produces the same result without errors.

**Examples:**
- Kernel modules: Check if loaded before loading
- Packages: Use package manager's idempotent install
- Configuration files: Template-based with checksums
- Services: Start only if not already running

### Separation of Concerns

- **System preparation**: Handled by `runtime` role's `common.yml`
- **Runtime installation**: Handled by runtime-specific task files
- **Kubernetes installation**: Handled by `k8s` role
- **No overlap**: Each role has clear responsibilities

### Fail Fast

The collection validates requirements early:
- Check CPU/memory/disk before installation
- Validate kernel version before proceeding
- Test network connectivity to registries
- Verify ports are available

If validation fails, deployment stops immediately with clear error messages.

### Configuration as Code

All configuration is defined in variables:
- No hardcoded values in tasks
- Everything customizable via variables
- Defaults in `defaults/main.yml`
- Overridable in playbooks or inventory

## Container Runtime Integration

### Runtime Selection

The collection supports multiple container runtimes through a plugin-like architecture:

```
runtime/tasks/main.yml
  │
  ├─> common.yml (always runs)
  │   - System prerequisites
  │   - Kernel configuration
  │
  ├─> containerd.yml (if container_runtime == "containerd")
  ├─> crio.yml (if container_runtime == "crio")
  ├─> docker.yml (if container_runtime == "docker")
  └─> podman.yml (if container_runtime == "podman")
```

### Runtime Configuration

Each runtime has:
1. **Task file**: Installation logic
2. **Template file**: Configuration file generation
3. **Service file**: Systemd unit definition
4. **Handler**: Service restart on config changes

**Example: containerd**
- Task: `tasks/containerd.yml`
- Template: `templates/containerd-config.toml.j2`
- Service: `files/containerd.service`
- Handler: Restart containerd on config change

### Build Methods

**Binary Installation:**
```
1. Download pre-built binary from official source
2. Extract to system directories
3. Create systemd service
4. Generate configuration
5. Start service
```

**Source Installation:**
```
1. Install Go compiler
2. Clone source repository
3. Build with make
4. Install binaries
5. Create systemd service
6. Generate configuration
7. Start service
```

### Registry Configuration

Runtimes are configured with:
- **Standard registries**: HTTPS endpoints (registry.k8s.io, quay.io, docker.io)
- **Insecure registries**: HTTP or self-signed certificates
- **Registry mirrors**: For improved performance
- **Authentication**: Pull secrets (if needed)

All registry configuration is templated and runtime-specific.

## Kubernetes Deployment Patterns

### Single-Node Architecture

The collection deploys Kubernetes in single-node mode:

```
┌───────────────────────────────────────┐
│ Single Node                            │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ Control Plane Components       │   │
│ │ - kube-apiserver               │   │
│ │ - kube-controller-manager      │   │
│ │ - kube-scheduler               │   │
│ │ - etcd                         │   │
│ └────────────────────────────────┘   │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ Node Components                │   │
│ │ - kubelet                      │   │
│ │ - kube-proxy                   │   │
│ │ - Container Runtime            │   │
│ └────────────────────────────────┘   │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ CNI Plugin                     │   │
│ │ - Calico/Flannel/Weave/Cilium │   │
│ └────────────────────────────────┘   │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ User Workloads                 │   │
│ │ - Deployments                  │   │
│ │ - Services                     │   │
│ │ - Pods                         │   │
│ └────────────────────────────────┘   │
└───────────────────────────────────────┘
```

**Key Aspects:**
- Master node is tainted to allow scheduling
- All components run on single node
- No HA or redundancy
- Suitable for development, edge, small workloads

### kubeadm Integration

The collection uses kubeadm for cluster initialization:

```yaml
# Generated kubeadm configuration
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
kubernetesVersion: v1.28.0
clusterName: my-cluster
networking:
  podSubnet: 10.244.0.0/16
  serviceSubnet: 10.96.0.0/12
```

**Workflow:**
1. Install kubeadm, kubelet, kubectl
2. Generate kubeadm config from template
3. Run `kubeadm init` with config
4. Configure kubectl for root/admin user
5. Untaint master node for workloads
6. Deploy CNI plugin

### CNI Plugin Deployment

CNI plugins are deployed via manifests:

```
For each CNI plugin:
  1. Fetch official manifest
  2. Apply to cluster
  3. Wait for pods to be ready
  4. Verify networking works
```

**CNI-Specific Behaviors:**
- **Calico**: Deploys operator + custom resources
- **Flannel**: Simple DaemonSet deployment
- **Weave**: DaemonSet with encryption options
- **Cilium**: Helm-based or manifest deployment

## Extensibility

### Adding New Container Runtimes

To add a new container runtime:

1. **Create task file**: `roles/runtime/tasks/newruntime.yml`
2. **Create template**: `roles/runtime/templates/newruntime-config.j2`
3. **Add systemd service**: `roles/runtime/files/newruntime.service`
4. **Update main task**: Include new runtime in conditional
5. **Add handler**: For service restarts
6. **Document**: Add to README and docs

**Example structure:**
```yaml
# tasks/newruntime.yml
- name: Install newruntime
  package:
    name: newruntime
    state: present

- name: Configure newruntime
  template:
    src: newruntime-config.j2
    dest: /etc/newruntime/config
  notify: Restart newruntime

- name: Start newruntime
  systemd:
    name: newruntime
    state: started
    enabled: yes
```

### Adding New CNI Plugins

To add a new CNI plugin:

1. **Add manifest**: Store CNI manifest in `roles/k8s/files/`
2. **Update task**: Add new CNI option to deployment task
3. **Test**: Verify networking works
4. **Document**: Update CNI plugin list

### Customizing Kubernetes Installation

For custom Kubernetes builds:

```yaml
k8s_install_from_source: true
k8s_repo: "https://github.com/yourorg/kubernetes"
k8s_branch: "custom-branch"
```

The role will:
1. Clone your repository
2. Build with your customizations
3. Install locally-built binaries
4. Continue normal cluster init

### Variable Override Patterns

**Low-level customization:**
```yaml
k8s_kubeadm_init_extra_args: "--your-custom-flag=value"
k8s_kubelet_extra_args: "--another-flag=value"
```

**Feature gates:**
```yaml
k8s_feature_gates:
  - "EphemeralContainers=true"
  - "CustomFeature=true"
```

## Performance Considerations

### Installation Speed

**Factors affecting speed:**
1. **Binary vs Source**: Binary is 5-10x faster
2. **Network speed**: Download time for images/binaries
3. **CPU power**: Affects compilation and cluster init
4. **Disk I/O**: Affects container image extraction

**Typical timings (binary installation):**
- Runtime installation: 2-5 minutes
- Kubernetes installation: 3-7 minutes
- Cluster initialization: 2-4 minutes
- CNI deployment: 1-3 minutes
- **Total: 8-19 minutes**

### Resource Usage

**During installation:**
- CPU: Moderate (higher for source builds)
- Memory: ~500MB-1GB
- Disk: ~5-10GB for binaries and images
- Network: ~2-4GB downloads

**After installation (idle cluster):**
- CPU: <1 core
- Memory: ~1-1.5GB
- Disk: ~10-15GB

### Optimization Tips

**Faster deployments:**
```yaml
# Skip network checks
k8s_check_network_connectivity: false

# Use binary installation
containerd_build_method: binary

# Use faster CNI
# CNI must be installed manually - flannel  # Simpler than Calico
```

**Production deployments:**
```yaml
# Full validation
k8s_check_network_connectivity: true

# Use production runtime
container_runtime: containerd

# Use feature-rich CNI
# CNI must be installed manually - calico
```

## Troubleshooting Architecture

### Log Locations

**Ansible logs:**
- Control node: Ansible output (terminal)
- Use `-vvv` for verbose output

**System logs (on target):**
```bash
# Container runtime
journalctl -u containerd
journalctl -u crio

# Kubernetes components
journalctl -u kubelet
journalctl -u kube-apiserver

# System messages
/var/log/syslog
/var/log/messages
```

### Common Failure Points

1. **SSH connectivity**: Test with `ssh user@host`
2. **Sudo privileges**: Test with `sudo whoami`
3. **Swap enabled**: Check with `swapon -s`
4. **Kernel modules**: Check with `lsmod | grep br_netfilter`
5. **Network connectivity**: Test registry access
6. **Port conflicts**: Check with `netstat -tuln`

### Debug Mode

Run with increased verbosity:
```bash
ansible-playbook deploy.yml -vvv
```

Check specific role:
```bash
ansible-playbook deploy.yml --tags=runtime -vvv
```

## Best Practices

### Development Workflow

1. **Use version control**: Track your playbooks
2. **Test in dev**: Don't test on production
3. **Pin versions**: Don't use "latest"
4. **Use tags**: For partial deployments
5. **Enable validation**: Catch errors early

### Production Deployment

1. **Review configuration**: Double-check all variables
2. **Test playbook**: Run in check mode first
3. **Backup**: Document node state
4. **Monitor**: Watch logs during deployment
5. **Validate**: Test cluster after deployment

### Maintenance

1. **Version upgrades**: Test in staging first
2. **Configuration changes**: Use version control
3. **Runtime updates**: May require node drain
4. **Kubernetes updates**: Follow official upgrade paths

For more information, see:
- [Getting Started Guide](getting-started.md)
- [Configuration Reference](configuration-reference.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Production Deployment Guide](production-deployment.md)
