# Ansible Collection - alancaldelas.kubernetes_baremetal

Ansible collection for deploying Kubernetes on bare-metal infrastructure. This collection provides automated installation and configuration of container runtimes and Kubernetes clusters on physical servers.

## Overview

This collection simplifies Kubernetes deployment on bare-metal by providing:
- **Container Runtime Support**: containerd, CRI-O, Docker, and Podman
- **Kubernetes Installation**: Single-node and multi-node cluster deployment via kubeadm
- **Hardware Management**: Custom modules for IPMI and Redfish operations
- **Multi-OS Support**: Debian/Ubuntu and RHEL/CentOS/Fedora

## Roles

### runtime
Installs and configures container runtimes with support for:
- Multiple runtimes (containerd, CRI-O, Docker, Podman)
- Binary or source installation
- Custom registry configuration
- System optimization for containers

[Documentation](roles/runtime/README.md)

### k8s
Deploys Kubernetes clusters using kubeadm with:
- System validation and prerequisites
- Container runtime integration
- Binary or source installation
- CNI plugin deployment (Calico, Flannel, Weave, Cilium)

### common_prereqs
Common system prerequisites and configuration tasks.

### hardware_validation
Hardware validation tasks for ensuring system requirements are met.

## Custom Modules

### ipmi_configuration
Ansible module for configuring servers via IPMI.

### redfish_iso_mount
Ansible module for mounting ISO images via Redfish API on BMC-enabled servers.

## Quick Start

```bash
# Install the collection
ansible-galaxy collection install alancaldelas.kubernetes_baremetal

# Deploy Kubernetes cluster
cat > deploy-k8s.yml <<EOF
---
- name: Deploy Kubernetes
  hosts: k8s_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.k8s
  vars:
    kubernetes_version: "1.28.0"
    k8s_container_runtime: containerd
    k8s_cni_plugin: calico
EOF

ansible-playbook -i inventory deploy-k8s.yml
```

## Documentation

Comprehensive documentation is available in the [docs/](docs/) directory:

- **[Getting Started](docs/getting-started.md)** - Installation and quick start
- **[Configuration Reference](docs/configuration-reference.md)** - All variables and options
- **[Production Deployment](docs/production-deployment.md)** - Best practices for production
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[Architecture](docs/architecture.md)** - Technical deep-dive

## Requirements

- Ansible 2.9+
- Target systems: Linux (Debian/Ubuntu, RHEL/CentOS/Fedora)
- Kernel 4.15+
- Minimum 2 CPU cores, 2GB RAM, 20GB disk

## License

MIT-0 / GPL-2.0-or-later

## Author

Alan Caldelas (ajcaldelas@gmail.com)
