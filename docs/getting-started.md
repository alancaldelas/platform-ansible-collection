# Getting Started with kubernetes_baremetal Collection

This guide will help you get started with the `alancaldelas.kubernetes_baremetal` Ansible collection for deploying single-node Kubernetes clusters on bare-metal infrastructure.

## Prerequisites

### Control Node Requirements

The **control node** is where you run Ansible (typically your laptop or workstation). It needs:

- **Ansible**: 2.9 or higher
- **Python**: 3.6+
- **SSH Access**: Ability to connect to target nodes
- **Network Access**: Can reach target nodes on SSH port (22)

**Note**: The control node does NOT need to be powerful - it just runs Ansible commands. All the heavy lifting happens on target nodes.

### Target Node Requirements

The **target nodes** are the bare-metal servers where Kubernetes will be installed. Each target node needs:

**Hardware:**
- Minimum 2 CPU cores
- Minimum 2GB RAM (4GB recommended for production)
- Minimum 20GB disk space

**Software:**
- Supported OS: Debian/Ubuntu, RHEL/CentOS/Fedora (already installed)
- Kernel version 4.15 or higher
- Root or sudo access
- SSH server running
- Network access to container registries (registry.k8s.io, quay.io, docker.io)

**Network:**
- Static IP or DHCP reservation (recommended)
- Unique hostname
- DNS resolution working

## Installation

### Step 1: Install the Collection

#### From Ansible Galaxy (when published)

```bash
ansible-galaxy collection install alancaldelas.kubernetes_baremetal
```

#### From Source

```bash
# Clone the repository
git clone <repository-url>
cd platform-ansible-collection

# Build the collection
ansible-galaxy collection build

# Install the collection
ansible-galaxy collection install alancaldelas-kubernetes_baremetal-*.tar.gz
```

### Step 2: Verify Installation

```bash
ansible-galaxy collection list | grep kubernetes_baremetal
```

You should see:
```
alancaldelas.kubernetes_baremetal   1.0.0
```

## Quick Start Examples

### Example 1: Complete Kubernetes Deployment

This is the most common use case - deploy a complete single-node Kubernetes cluster.

**Step 1**: Create an inventory file `inventory.ini`:

```ini
[k8s_nodes]
192.168.1.100 ansible_user=ubuntu

[all:vars]
ansible_become=yes
```

**Step 2**: Create a playbook `deploy-k8s.yml`:

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
    k8s_cluster_name: my-cluster
```

**Step 3**: Run the playbook:

```bash
ansible-playbook -i inventory.ini deploy-k8s.yml
```

**What this does:**
1. Validates system requirements on target node
2. Loads kernel modules and configures sysctl
3. Disables swap
4. Installs containerd container runtime
5. Installs kubeadm, kubelet, kubectl
6. Initializes single-node cluster
7. Deploys Calico CNI plugin
8. Configures kubectl access

### Example 2: Install Container Runtime Only

If you want to install just the container runtime without Kubernetes:

```yaml
---
- name: Install containerd
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.runtime
  vars:
    container_runtime: containerd
    container_runtime_version: "1.7.2"
```

Run it:
```bash
ansible-playbook -i inventory.ini runtime-only.yml
```

### Example 3: Kubernetes with CRI-O Runtime

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
    k8s_cluster_name: my-cluster
```

### Example 4: Custom Network Configuration

```yaml
---
- name: Kubernetes with custom networks
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_pod_subnet: "192.168.0.0/16"  # Must match CNI plugin requirements
    k8s_service_subnet: "10.100.0.0/16"
```

## Post-Installation

### Install CNI Plugin (Required)

**Important:** After the Ansible playbook completes, your cluster nodes will be in `NotReady` state. You must install a CNI (Container Network Interface) plugin to make your cluster functional.

**Popular CNI options:**
- [Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/) - Production-ready, network policies
- [Flannel](https://github.com/flannel-io/flannel) - Simple, easy to setup
- [Cilium](https://docs.cilium.io/en/stable/gettingstarted/k8s-install-default/) - eBPF-based, advanced features

SSH to the target node and follow the official installation guide for your chosen CNI plugin. Ensure the pod CIDR matches `k8s_pod_subnet` (default: 10.244.0.0/16).

### Accessing Your Cluster

After CNI plugin installation, verify your cluster is working:

```bash
# Check cluster status (nodes should now be Ready)
kubectl get nodes

# Check all system pods are running
kubectl get pods -A

# View cluster info
kubectl cluster-info

# Test DNS resolution
kubectl run test --image=busybox --rm -it --restart=Never -- nslookup kubernetes.default
```

### Copy kubeconfig to Control Node (Optional)

To manage the cluster from your control node:

```bash
# From control node
scp ubuntu@192.168.1.100:/etc/kubernetes/admin.conf ~/.kube/config

# Now you can use kubectl locally
kubectl get nodes
```

## Understanding the Deployment Flow

```
┌────────────────────────────────────────┐
│ Your Laptop/Workstation                │
│ (Control Node)                         │
│                                         │
│ 1. Run: ansible-playbook deploy.yml   │
└───────────┬────────────────────────────┘
            │
            │ SSH Connection
            │ Ansible runs tasks on target
            ↓
┌────────────────────────────────────────┐
│ Bare-Metal Server                      │
│ (Target Node)                          │
│                                         │
│ 2. System prep (kernel, sysctl, swap) │
│ 3. Install container runtime          │
│ 4. Install Kubernetes components      │
│ 5. Initialize cluster                 │
│ 6. Deploy CNI plugin                  │
│                                         │
│ Result: Running Kubernetes cluster    │
└────────────────────────────────────────┘
```

## Common First-Time Issues

### Issue: "Connection refused" to nodes

**Cause**: Ansible cannot SSH to target node

**Solution**: Verify SSH connectivity:
```bash
# Test SSH connection from control node
ssh ubuntu@192.168.1.100

# If password prompted, set up SSH keys
ssh-copy-id ubuntu@192.168.1.100
```

### Issue: "Permission denied" errors

**Cause**: User doesn't have sudo privileges

**Solution**: Ensure user can sudo:
```bash
# On target node, test sudo
sudo whoami

# If it fails, add user to sudo group (as root)
usermod -aG sudo ubuntu
```

### Issue: Container runtime fails to install

**Cause**: Network connectivity or DNS resolution issues

**Solution**: Test connectivity from target node:
```bash
# SSH to target node
ssh ubuntu@192.168.1.100

# Test DNS and connectivity
ping 8.8.8.8
curl -I https://registry.k8s.io
curl -I https://github.com
```

### Issue: Swap is still enabled

**Cause**: Swap configuration persists after reboot

**Solution**: The role disables swap, but verify:
```bash
# Check swap status
swapon -s

# If swap is on, the role will disable it
# But verify /etc/fstab has swap entries commented out
```

### Issue: Pods stay in "Pending" state

**Cause**: CNI plugin not deployed or not ready

**Solution**: Check CNI pods:
```bash
kubectl get pods -n kube-system

# Look for calico/flannel/cilium pods
# They should all be Running
```

### Issue: kubectl command not found

**Cause**: PATH not set or kubectl not installed

**Solution**: Set up kubectl path:
```bash
# Check if kubectl exists
which kubectl

# If not in PATH, add it
export PATH=$PATH:/usr/bin

# Or use full path
/usr/bin/kubectl get nodes
```

## Next Steps

After successfully deploying your cluster:

1. **Deploy Applications**: Start deploying workloads to your cluster
   ```bash
   kubectl create deployment nginx --image=nginx
   kubectl expose deployment nginx --port=80 --type=NodePort
   ```

2. **Explore Configuration**: Check the [Configuration Reference](configuration-reference.md) for all available options

3. **Production Setup**: See [Production Deployment Guide](production-deployment.md) for best practices

4. **Troubleshooting**: Refer to the [Troubleshooting Guide](troubleshooting.md) if you encounter issues

5. **Architecture**: Review [Architecture Overview](architecture.md) to understand how the roles work

## Getting Help

- **Collection README**: [Main documentation](../README.md)
- **Role Documentation**:
  - [runtime role README](../roles/runtime/README.md)
  - [k8s role README](../roles/k8s/README.md)
- **GitHub Issues**: Report bugs and request features at the repository

## Additional Resources

- [Kubernetes Official Documentation](https://kubernetes.io/docs/)
- [kubeadm Documentation](https://kubernetes.io/docs/reference/setup-tools/kubeadm/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

## Frequently Asked Questions

**Q: Can I deploy multi-node clusters?**
A: Not currently. This collection only supports single-node deployments.

**Q: Can I use this for production?**
A: Single-node clusters have limitations (no HA). See the [Production Deployment Guide](production-deployment.md) for considerations.

**Q: What if I already have a container runtime installed?**
A: Set `k8s_manage_container_runtime: false` and the k8s role will skip runtime installation.

**Q: Can I customize the Kubernetes version?**
A: Yes, set `kubernetes_version: "1.xx.x"` to any supported version.

**Q: Does this work on virtual machines?**
A: Yes! As long as they run a supported Linux distribution and meet the requirements.

**Q: Can I install from sources instead of binaries?**
A: Yes, set `k8s_install_from_source: true` for Kubernetes and `containerd_build_method: source` for the runtime.
