# Playbooks Quick Reference

Quick command reference for all sample playbooks in this collection.

## Runtime Installations

| Playbook | Runtime | Command |
|----------|---------|---------|
| `runtime-containerd.yml` | containerd | `ansible-playbook -i inventory playbooks/runtime-containerd.yml` |
| `runtime-crio.yml` | CRI-O | `ansible-playbook -i inventory playbooks/runtime-crio.yml` |
| `runtime-docker.yml` | Docker | `ansible-playbook -i inventory playbooks/runtime-docker.yml` |
| `runtime-podman.yml` | Podman | `ansible-playbook -i inventory playbooks/runtime-podman.yml` |

## Kubernetes Deployments

| Playbook | Description | Requirements |
|----------|-------------|--------------|
| `k8s-single-node-basic.yml` | Basic dev/test cluster | 2 CPU, 2GB RAM, 20GB disk |
| `k8s-production-validated.yml` | Production cluster with validation | 4 CPU, 8GB RAM, 100GB disk |
| `k8s-from-source.yml` | Build K8s from source | 4 CPU, 8GB RAM, 50GB disk |

## CNI-Specific Deployments

| Playbook | CNI Plugin | Pod CIDR | Features |
|----------|-----------|----------|----------|
| `k8s-calico-cni.yml` | Calico | 192.168.0.0/16 | Network policies, BGP, production |
| `k8s-flannel-cni.yml` | Flannel | 10.244.0.0/16 | Simple, VXLAN, easy setup |
| `k8s-weave-cni.yml` | Weave Net | 10.32.0.0/12 | Mesh, encryption, multi-cloud |
| `k8s-cilium-cni.yml` | Cilium | 10.0.0.0/8 | eBPF, L7 policies, high perf |

## Special Scenarios

| Playbook | Use Case | Command |
|----------|----------|---------|
| `full-stack-deployment.yml` | Runtime + K8s with phases | `ansible-playbook -i inventory playbooks/full-stack-deployment.yml` |
| `hardware-validation.yml` | Pre-deployment validation | `ansible-playbook -i inventory playbooks/hardware-validation.yml` |
| `airgap-offline-installation.yml` | Air-gapped/offline install | `ansible-playbook -i inventory playbooks/airgap-offline-installation.yml` |

## Common Inventory Template

```ini
[k8s_nodes]
node1 ansible_host=192.168.1.100 ansible_user=ubuntu

[k8s_nodes:vars]
ansible_become=yes
```

## Common Variable Overrides

```bash
# Change Kubernetes version
ansible-playbook -i inventory playbooks/k8s-single-node-basic.yml \
  -e "kubernetes_version=1.29.0"

# Change CNI plugin
ansible-playbook -i inventory playbooks/k8s-single-node-basic.yml \
  -e "k8s_cni_plugin=flannel"

# Use different runtime
ansible-playbook -i inventory playbooks/k8s-single-node-basic.yml \
  -e "k8s_container_runtime=crio"

# Custom network CIDRs
ansible-playbook -i inventory playbooks/k8s-single-node-basic.yml \
  -e "k8s_pod_subnet=10.100.0.0/16" \
  -e "k8s_service_subnet=10.200.0.0/16"
```

## Tags for Full Stack Deployment

```bash
# Run only runtime installation
ansible-playbook -i inventory playbooks/full-stack-deployment.yml --tags runtime

# Run only Kubernetes installation
ansible-playbook -i inventory playbooks/full-stack-deployment.yml --tags kubernetes

# Run only verification
ansible-playbook -i inventory playbooks/full-stack-deployment.yml --tags verify
```

## Decision Tree

```
What do you want to do?

├─ Install container runtime only
│  └─ Which runtime?
│     ├─ containerd (recommended) → runtime-containerd.yml
│     ├─ CRI-O (k8s-native) → runtime-crio.yml
│     ├─ Docker (legacy) → runtime-docker.yml
│     └─ Podman (daemonless) → runtime-podman.yml
│
├─ Install Kubernetes
│  ├─ First time / Learning
│  │  └─ k8s-single-node-basic.yml
│  │
│  ├─ Production deployment
│  │  └─ k8s-production-validated.yml
│  │
│  ├─ Need specific CNI
│  │  ├─ Calico (network policies) → k8s-calico-cni.yml
│  │  ├─ Flannel (simple) → k8s-flannel-cni.yml
│  │  ├─ Weave (mesh, encryption) → k8s-weave-cni.yml
│  │  └─ Cilium (eBPF, advanced) → k8s-cilium-cni.yml
│  │
│  └─ Development / Custom build
│     └─ k8s-from-source.yml
│
├─ Full stack (runtime + k8s with control)
│  └─ full-stack-deployment.yml
│
├─ Validate hardware first
│  └─ hardware-validation.yml
│
└─ Air-gapped / Offline environment
   └─ airgap-offline-installation.yml
```

## Verification Commands

After any Kubernetes deployment:

```bash
# SSH to node
ssh user@node-ip

# Setup kubectl
mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Check cluster
kubectl get nodes
kubectl get pods -A
kubectl cluster-info

# Check CNI
kubectl get pods -n kube-system -l k8s-app=calico-node  # Calico
kubectl get pods -n kube-system -l app=flannel          # Flannel
kubectl get pods -n kube-system -l name=weave-net       # Weave
kubectl get pods -n kube-system -l k8s-app=cilium       # Cilium
```

## File Sizes

Total: 2282 lines across 15 playbooks + README

- Runtime playbooks: ~2.2KB each (4 playbooks)
- Basic K8s playbooks: ~2.3-2.7KB each (4 CNI playbooks)
- Advanced playbooks: ~3.9-7.8KB (5 playbooks)
- Documentation: ~14KB README + this reference

## See Also

- Full documentation: [README.md](README.md)
- Collection docs: [../docs/](../docs/)
- Role docs: [../roles/*/README.md](../roles/)
