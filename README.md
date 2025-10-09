# platform-ansible-collection
Ansible Collection to install various K8s deployments specifically for Bare Metal

### Install from Source

```bash
git clone https://github.com/alancaldelas/kubernetes_baremetal.git
cd kubernetes_baremetal
ansible-galaxy collection build
ansible-galaxy collection install alancaldelas-kubernetes_baremetal-*.tar.gz
```

### Verify Installation

```bash
ansible-galaxy collection list | grep kubernetes_baremetal
```

## Quick Start

### Basic Kubernetes Installation

Create a playbook `deploy-k8s.yml`:

```yaml
---
- name: Deploy Kubernetes on bare metal
  hosts: kubernetes_nodes
  become: yes

  roles:
    # First install container runtime
    - role: alancaldelas.kubernetes_baremetal.runtime
      vars:
        container_runtime: containerd
        container_runtime_version: "2.1.4"

    # Then install Kubernetes
    - role: alancaldelas.kubernetes_baremetal.k8s
      vars:
        kubernetes_version: "1.33.0"
        k8s_container_runtime: containerd
```

Create inventory file
```
[kubernetes_nodes]
node1 ansible_host=<Some IP> ansible_become=yes ansible_ssh_private_key_file=~/.ssh/id_rsa
```

Run the playbook:

```bash
ansible-playbook -i inventory.ini deploy-k8s.yml

