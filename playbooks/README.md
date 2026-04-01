# Sample Playbooks

This directory contains comprehensive sample playbooks demonstrating all installation scenarios supported by the `alancaldelas.kubernetes_baremetal` collection.

## Table of Contents

- [Container Runtime Playbooks](#container-runtime-playbooks)
- [Kubernetes Deployment Playbooks](#kubernetes-deployment-playbooks)
- [CNI Plugin Specific Playbooks](#cni-plugin-specific-playbooks)
- [Advanced Deployment Scenarios](#advanced-deployment-scenarios)
- [Quick Start Guide](#quick-start-guide)

## Container Runtime Playbooks

These playbooks install container runtimes independently, without Kubernetes. Use these when you want to set up the runtime separately or test different runtime configurations.

### runtime-containerd.yml
Installs the containerd container runtime (recommended for production).
```bash
ansible-playbook -i inventory playbooks/runtime-containerd.yml
```

**Features:**
- Binary or source installation
- Custom registry configuration
- Storage and logging settings
- Production-ready defaults

**Use cases:**
- Standard Kubernetes deployments
- Production environments
- When you need CRI compatibility

---

### runtime-crio.yml
Installs the CRI-O container runtime (Kubernetes-native, lightweight).
```bash
ansible-playbook -i inventory playbooks/runtime-crio.yml
```

**Features:**
- Kubernetes-native runtime
- Matches Kubernetes version
- Minimal resource overhead
- Built-in security features

**Use cases:**
- Kubernetes-only environments
- Resource-constrained systems
- When you prioritize Kubernetes integration

---

### runtime-docker.yml
Installs Docker container runtime (legacy support only).
```bash
ansible-playbook -i inventory playbooks/runtime-docker.yml
```

**Note:** Docker support was removed from Kubernetes v1.24+. This playbook is provided for legacy systems only. Use containerd or CRI-O for new deployments.

---

### runtime-podman.yml
Installs Podman container runtime (daemonless alternative to Docker).
```bash
ansible-playbook -i inventory playbooks/runtime-podman.yml
```

**Features:**
- Daemonless architecture
- Rootless container support
- Docker-compatible CLI
- Red Hat ecosystem integration

**Use cases:**
- Development environments
- CI/CD pipelines
- When you prefer daemonless architecture

---

## Kubernetes Deployment Playbooks

These playbooks deploy complete Kubernetes clusters with various configurations.

### k8s-single-node-basic.yml
The simplest Kubernetes deployment with default settings.
```bash
ansible-playbook -i inventory playbooks/k8s-single-node-basic.yml
```

**Features:**
- Default configuration
- Automatic runtime installation (containerd)
- Calico CNI by default
- Minimal configuration needed

**Perfect for:**
- First-time deployments
- Development and testing
- Learning Kubernetes
- Proof of concepts

**Requirements:**
- 2 CPU cores
- 2GB RAM
- 20GB disk

---

### k8s-production-validated.yml
Production-ready deployment with hardware validation and enhanced settings.
```bash
ansible-playbook -i inventory playbooks/k8s-production-validated.yml
```

**Features:**
- Pre-deployment hardware validation
- Higher resource requirements
- Enhanced logging (50Mi logs, 5 files)
- Custom network configuration
- SELinux support (RHEL/CentOS)
- Firewall configuration
- Kubelet resource reservations
- Feature gates enabled

**Perfect for:**
- Production deployments
- Enterprise environments
- When reliability is critical
- Compliance requirements

**Requirements:**
- 4 CPU cores
- 8GB RAM
- 100GB disk

---

## CNI Plugin Specific Playbooks

These playbooks deploy Kubernetes with specific CNI (Container Network Interface) plugins. Each CNI has different features and performance characteristics.

### k8s-calico-cni.yml
Kubernetes with Calico CNI (recommended for production).
```bash
ansible-playbook -i inventory playbooks/k8s-calico-cni.yml
```

**Features:**
- Network policy support (L3/L4)
- BGP routing support
- IP-in-IP or VXLAN encapsulation
- High performance
- Enterprise-grade security

**Pod CIDR:** 192.168.0.0/16 (Calico default)

**Best for:**
- Production environments
- Multi-tenant clusters
- When you need network policies
- Large-scale deployments

---

### k8s-flannel-cni.yml
Kubernetes with Flannel CNI (simple overlay network).
```bash
ansible-playbook -i inventory playbooks/k8s-flannel-cni.yml
```

**Features:**
- Simple overlay networking
- VXLAN backend
- Easy setup and troubleshooting
- Minimal configuration

**Pod CIDR:** 10.244.0.0/16 (Flannel default)

**Best for:**
- Small to medium clusters
- Development environments
- Simple networking requirements
- Quick deployments

**Note:** Flannel does not support network policies.

---

### k8s-weave-cni.yml
Kubernetes with Weave Net CNI (mesh networking).
```bash
ansible-playbook -i inventory playbooks/k8s-weave-cni.yml
```

**Features:**
- Automatic mesh networking
- Network policy support
- Optional encryption
- Multi-cloud support
- Simple installation

**Pod CIDR:** 10.32.0.0/12 (Weave default)

**Best for:**
- Multi-cloud deployments
- When encryption is needed
- Hybrid cloud scenarios
- Dynamic environments

---

### k8s-cilium-cni.yml
Kubernetes with Cilium CNI (eBPF-based networking).
```bash
ansible-playbook -i inventory playbooks/k8s-cilium-cni.yml
```

**Features:**
- eBPF-based networking
- L3-L7 network policies
- Service mesh capabilities
- Transparent encryption
- Hubble observability
- High performance

**Pod CIDR:** 10.0.0.0/8 (Cilium default)

**Requirements:**
- Kernel 4.19+ (5.10+ recommended)
- eBPF support

**Best for:**
- Advanced networking needs
- Service mesh without sidecar
- Deep observability requirements
- High-performance environments
- Modern kernel systems

---

## Advanced Deployment Scenarios

### k8s-from-source.yml
Build and install Kubernetes from source code.
```bash
ansible-playbook -i inventory playbooks/k8s-from-source.yml
```

**Features:**
- Compile Kubernetes from GitHub
- Custom patches and modifications
- Bleeding-edge features
- Development and testing

**Build time:** 30-60 minutes

**Requirements:**
- 4 CPU cores
- 8GB RAM
- 50GB disk
- Stable internet connection
- Go compiler (installed automatically)

**Perfect for:**
- Kubernetes development
- Testing custom patches
- Contributing to Kubernetes
- Research and experimentation

**Warning:** This takes significantly longer than binary installation. Ensure you have time and resources.

---

### full-stack-deployment.yml
Complete deployment with explicit runtime and Kubernetes installation phases.
```bash
ansible-playbook -i inventory playbooks/full-stack-deployment.yml
```

**Features:**
- Explicit control over each phase
- Custom runtime configuration
- Separate runtime and K8s installation
- Detailed verification steps
- Tagged phases for selective execution

**Phases:**
1. Container runtime installation
2. Kubernetes deployment
3. Cluster verification

**Run specific phases:**
```bash
# Install only runtime
ansible-playbook -i inventory playbooks/full-stack-deployment.yml --tags runtime

# Install only Kubernetes
ansible-playbook -i inventory playbooks/full-stack-deployment.yml --tags kubernetes

# Run verification only
ansible-playbook -i inventory playbooks/full-stack-deployment.yml --tags verify
```

**Perfect for:**
- Understanding the deployment process
- Custom configurations
- Troubleshooting specific phases
- Educational purposes

---

### hardware-validation.yml
Validate hardware before Kubernetes deployment.
```bash
ansible-playbook -i inventory playbooks/hardware-validation.yml
```

**Features:**
- CPU core validation
- RAM validation
- Disk space validation
- Network interface validation
- Kernel version check
- BMC/IPMI validation (optional)
- Hardware report generation

**Validations performed:**
- Minimum CPU cores: 2 (configurable)
- Minimum RAM: 4GB (configurable)
- Minimum disk: 50GB (configurable)
- Network interfaces: 1+ (configurable)
- Kernel version: 4.15+

**Perfect for:**
- Pre-deployment checks
- Hardware inventory
- Ensuring compatibility
- Capacity planning

**Output:** Generates a hardware report in `/tmp/hardware-validation-*.txt`

---

### ramdisk-boot-deployment.yml
Deploy Kubernetes on ramdisk-booted systems (PXE, network boot, diskless nodes).
```bash
ansible-playbook -i inventory playbooks/ramdisk-boot-deployment.yml
```

**Features:**
- Sets `container_no_pivot_root: true` for ramdisk compatibility
- Validates ramdisk root filesystem
- Checks sufficient RAM availability
- Configures both containerd and CRI-O for ramdisk operation
- Provides persistent storage recommendations

**Use Cases:**
- Network boot (PXE/iPXE) environments
- Diskless compute nodes
- Live boot systems
- Stateless infrastructure

**Special Configuration:**
- Disables pivot_root syscall (uses MS_MOVE instead)
- Recommends 4GB+ RAM minimum
- Provides guidance on persistent storage mounting

**Critical Setting:**
```yaml
container_no_pivot_root: true  # Required for ramdisk boot
```

**When to use:** Your servers boot from network/ramdisk and you get "pivot_root: invalid argument" errors with standard container runtimes.

---

### airgap-offline-installation.yml
Deploy Kubernetes in air-gapped/offline environments.
```bash
ansible-playbook -i inventory playbooks/airgap-offline-installation.yml
```

**Features:**
- No internet connectivity required
- Local container registry support
- Local package repository support
- Insecure registry configuration
- Pre-staging instructions included

**Prerequisites:**
1. Local container registry with all images
2. Local package mirrors (apt/yum)
3. Pre-downloaded binaries
4. Network connectivity to local resources

**Images to pre-pull:**
- kube-apiserver, kube-controller-manager, kube-scheduler, kube-proxy
- etcd, coredns, pause
- CNI plugin images (Calico/Flannel/etc.)

**Perfect for:**
- Secure/isolated environments
- Compliance requirements (SOC2, HIPAA)
- No internet access
- On-premise deployments
- High-security environments

**See playbook comments for complete pre-staging checklist.**

---

## Quick Start Guide

### 1. Choose Your Scenario

**I want to quickly test Kubernetes:**
→ Use `k8s-single-node-basic.yml`

**I want a production deployment:**
→ Use `k8s-production-validated.yml`

**I need a specific CNI:**
→ Use `k8s-calico-cni.yml`, `k8s-flannel-cni.yml`, `k8s-weave-cni.yml`, or `k8s-cilium-cni.yml`

**I want to install just the container runtime:**
→ Use `runtime-containerd.yml`, `runtime-crio.yml`, etc.

**I'm in an air-gapped environment:**
→ Use `airgap-offline-installation.yml`

**I need to validate hardware first:**
→ Use `hardware-validation.yml`

---

### 2. Create Your Inventory

Create a file named `inventory.ini`:

```ini
[k8s_nodes]
k8s-node1 ansible_host=192.168.1.100 ansible_user=ubuntu

[k8s_nodes:vars]
ansible_become=yes
```

Or for production:

```ini
[k8s_production]
prod-k8s-01 ansible_host=10.0.1.100 ansible_user=admin

[k8s_production:vars]
ansible_become=yes
ansible_ssh_private_key_file=~/.ssh/prod_key
```

---

### 3. Run the Playbook

```bash
# Basic syntax
ansible-playbook -i inventory.ini playbooks/<playbook-name>.yml

# With verbose output
ansible-playbook -i inventory.ini playbooks/<playbook-name>.yml -v

# Check mode (dry run)
ansible-playbook -i inventory.ini playbooks/<playbook-name>.yml --check

# With extra variables
ansible-playbook -i inventory.ini playbooks/<playbook-name>.yml \
  -e "kubernetes_version=1.28.0" \
  -e "k8s_cni_plugin=calico"
```

---

### 4. Verify Installation

After the playbook completes:

```bash
# SSH to the node
ssh ubuntu@192.168.1.100

# Copy kubeconfig
mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Check cluster
kubectl get nodes
kubectl get pods -A

# Verify CNI is running
kubectl get pods -n kube-system
```

---

## Common Configuration Variables

All playbooks support these common variables (set in the playbook or via `-e`):

### Kubernetes Settings
```yaml
kubernetes_version: "1.28.0"          # K8s version to install
k8s_cluster_name: my-cluster          # Cluster name
k8s_pod_subnet: "10.244.0.0/16"       # Pod network CIDR
k8s_service_subnet: "10.96.0.0/12"    # Service network CIDR
k8s_cni_plugin: calico                # CNI: calico, flannel, weave, cilium
```

### Container Runtime Settings
```yaml
k8s_container_runtime: containerd     # containerd, crio, docker, podman
container_runtime_version: "1.7.2"    # Runtime version
containerd_build_method: binary       # binary or source
```

### System Requirements
```yaml
k8s_min_cpu_cores: 2                  # Minimum CPU cores
k8s_min_memory_mb: 2048               # Minimum RAM in MB
k8s_min_disk_space_gb: 20             # Minimum disk in GB
k8s_min_kernel_version: "4.15"        # Minimum kernel version
```

### Registry Configuration
```yaml
container_registries:
  - registry.k8s.io
  - quay.io
  - docker.io

container_insecure_registries:       # HTTP or self-signed
  - localhost:5000
```

---

## Troubleshooting

### Playbook fails with "Connection refused"
- Verify SSH connectivity: `ssh user@host`
- Check SSH keys are configured: `ssh-copy-id user@host`
- Ensure ansible_user is correct in inventory

### Playbook fails with "Permission denied"
- Ensure user has sudo access: `sudo whoami`
- Add user to sudo group: `usermod -aG sudo username`
- Check `ansible_become=yes` is set in inventory

### Container runtime fails to start
- Check disk space: `df -h`
- Check systemd logs: `journalctl -u containerd -f`
- Verify network connectivity to registries

### Kubernetes pods stuck in Pending
- Check CNI pods are running: `kubectl get pods -n kube-system`
- Verify pod network CIDR matches CNI configuration
- Check node is Ready: `kubectl get nodes`

### Network connectivity checks fail (air-gapped)
- Set `k8s_check_network_connectivity: false`
- Set `k8s_required_endpoints: []`
- Use `airgap-offline-installation.yml`

---

## Additional Resources

- **Collection README**: [../README.md](../README.md)
- **Getting Started Guide**: [../docs/getting-started.md](../docs/getting-started.md)
- **Configuration Reference**: [../docs/configuration-reference.md](../docs/configuration-reference.md)
- **Production Deployment**: [../docs/production-deployment.md](../docs/production-deployment.md)
- **Troubleshooting Guide**: [../docs/troubleshooting.md](../docs/troubleshooting.md)

### Role Documentation
- **Runtime Role**: [../roles/runtime/README.md](../roles/runtime/README.md)
- **K8s Role**: [../roles/k8s/README.md](../roles/k8s/README.md)
- **Hardware Validation Role**: [../roles/hardware_validation/README.md](../roles/hardware_validation/README.md)
- **Common Prerequisites Role**: [../roles/common_prereqs/README.md](../roles/common_prereqs/README.md)

---

## Contributing

When creating new sample playbooks:

1. Use descriptive filenames
2. Include comprehensive comments
3. Add example inventory inline
4. Document all variables
5. Explain use cases clearly
6. Test on all supported OS families
7. Update this README

---

## License

MIT-0 / GPL-2.0-or-later

---

## Support

For issues, questions, or contributions, please refer to the main collection repository.

Created by Alan Caldelas (ajcaldelas@gmail.com)
