# Troubleshooting Guide

Comprehensive troubleshooting guide for the `alancaldelas.kubernetes_baremetal` collection.

## Table of Contents

- [General Ansible Issues](#general-ansible-issues)
- [Container Runtime Issues](#container-runtime-issues)
- [Kubernetes Deployment Issues](#kubernetes-deployment-issues)
- [Network Issues](#network-issues)
- [Post-Deployment Issues](#post-deployment-issues)
- [Debugging Tips](#debugging-tips)
- [Getting Further Help](#getting-further-help)

## General Ansible Issues

### Connection Timeout

**Symptom:**
```
TASK [Gathering Facts] ****************************
fatal: [node1]: UNREACHABLE! => {"changed": false, "msg": "Failed to connect to the host via ssh: Connection timed out"}
```

**Causes:**
- SSH service not running on target node
- Firewall blocking SSH port
- Incorrect IP address
- Network routing issues

**Solutions:**

1. **Test SSH manually:**
   ```bash
   ssh user@target-node-ip
   ```

2. **Check SSH service on target:**
   ```bash
   systemctl status sshd
   ```

3. **Verify firewall allows SSH:**
   ```bash
   # On target node
   sudo firewall-cmd --list-ports
   sudo ufw status
   ```

4. **Check network connectivity:**
   ```bash
   ping target-node-ip
   traceroute target-node-ip
   ```

### Permission Denied

**Symptom:**
```
fatal: [node1]: FAILED! => {"msg": "Missing sudo password"}
```

**Causes:**
- User doesn't have sudo privileges
- Sudo password required but not provided
- `ansible_become: yes` not set

**Solutions:**

1. **Ensure user has sudo privileges:**
   ```bash
   # On target node
   sudo usermod -aG sudo username
   ```

2. **Test sudo access:**
   ```bash
   ssh user@node1 'sudo whoami'
   ```

3. **Configure passwordless sudo (recommended):**
   ```bash
   # On target node
   echo "username ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/username
   ```

4. **Use --ask-become-pass:**
   ```bash
   ansible-playbook deploy.yml -K
   ```

### Module Not Found

**Symptom:**
```
ERROR! couldn't resolve module/action 'community.general.modprobe'
```

**Cause:**
- Missing Ansible collection dependencies

**Solution:**
```bash
ansible-galaxy collection install community.general
```

## Container Runtime Issues

### Service Fails to Start

**Symptom:**
```
TASK [runtime : Start containerd] *****************
fatal: [node1]: FAILED! => {"msg": "Unable to start service containerd: Job for containerd.service failed"}
```

**Causes:**
- Configuration error
- Missing dependencies
- Port already in use
- Corrupted binary

**Solutions:**

1. **Check service status:**
   ```bash
   sudo systemctl status containerd
   sudo journalctl -u containerd -n 50
   ```

2. **Validate configuration:**
   ```bash
   # For containerd
   sudo containerd config dump

   # For CRI-O
   sudo crio config
   ```

3. **Check for port conflicts:**
   ```bash
   sudo netstat -tuln | grep LISTEN
   sudo lsof -i -P -n | grep LISTEN
   ```

4. **Reinstall runtime:**
   ```bash
   # Set containerd_build_method: binary in playbook
   ansible-playbook deploy.yml --tags=runtime
   ```

### Registry Connection Failures

**Symptom:**
```
failed to pull image "registry.k8s.io/pause:3.9": failed to pull and unpack image
```

**Causes:**
- Network connectivity issues
- DNS resolution failures
- Firewall blocking HTTPS
- Registry authentication required

**Solutions:**

1. **Test registry access from target node:**
   ```bash
   curl -I https://registry.k8s.io
   curl -I https://quay.io
   curl -I https://docker.io
   ```

2. **Check DNS resolution:**
   ```bash
   nslookup registry.k8s.io
   dig registry.k8s.io
   ```

3. **Test image pull manually:**
   ```bash
   # For containerd
   sudo ctr image pull registry.k8s.io/pause:3.9

   # For CRI-O
   sudo crictl pull registry.k8s.io/pause:3.9
   ```

4. **Configure proxy if needed:**
   ```yaml
   # In playbook variables
   http_proxy: "http://proxy.company.com:8080"
   https_proxy: "http://proxy.company.com:8080"
   no_proxy: "localhost,127.0.0.1"
   ```

### Build from Source Fails

**Symptom:**
```
TASK [runtime : Build containerd from source] *****
fatal: [node1]: FAILED! => {"msg": "go: command not found"}
```

**Causes:**
- Missing build dependencies
- Insufficient disk space
- Incorrect Go version
- Network issues during git clone

**Solutions:**

1. **Install build dependencies manually:**
   ```bash
   # Debian/Ubuntu
   sudo apt-get install build-essential git golang-1.21

   # RHEL/CentOS
   sudo dnf groupinstall "Development Tools"
   sudo dnf install git golang
   ```

2. **Check disk space:**
   ```bash
   df -h
   ```

3. **Use binary installation instead:**
   ```yaml
   containerd_build_method: binary  # Faster and more reliable
   ```

## Kubernetes Deployment Issues

### kubeadm init Fails

**Symptom:**
```
TASK [k8s : Initialize Kubernetes cluster] ********
fatal: [node1]: FAILED! => {"msg": "kubeadm init failed"}
```

**Common Causes & Solutions:**

#### Swap Not Disabled

**Error:**
```
[ERROR Swap]: running with swap on is not supported. Please disable swap
```

**Solution:**
```bash
# On target node
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Verify
swapon -s  # Should show nothing
```

#### Port Already in Use

**Error:**
```
[ERROR Port-6443]: Port 6443 is in use
```

**Solution:**
```bash
# Find what's using the port
sudo netstat -tuln | grep 6443
sudo lsof -i :6443

# If old Kubernetes installation, reset it
sudo kubeadm reset -f
```

#### Container Runtime Not Running

**Error:**
```
[ERROR CRI]: container runtime is not running
```

**Solution:**
```bash
# Check runtime status
sudo systemctl status containerd
sudo systemctl status crio

# Start runtime
sudo systemctl start containerd
sudo systemctl enable containerd
```

### Kernel Modules Not Loaded

**Symptom:**
```
TASK [k8s : Load required kernel modules] *********
fatal: [node1]: FAILED! => {"msg": "modprobe: FATAL: Module br_netfilter not found"}
```

**Cause:**
- Kernel too old
- Module not available in kernel

**Solutions:**

1. **Check kernel version:**
   ```bash
   uname -r
   ```

2. **Install kernel modules:**
   ```bash
   # Debian/Ubuntu
   sudo apt-get install linux-modules-extra-$(uname -r)

   # RHEL/CentOS
   sudo dnf install kernel-modules-extra
   ```

3. **Manually load modules:**
   ```bash
   sudo modprobe overlay
   sudo modprobe br_netfilter
   sudo modprobe ip_vs
   ```

### Kubelet Not Starting

**Symptom:**
```
kubelet.service: Main process exited, code=exited, status=1/FAILURE
```

**Solutions:**

1. **Check kubelet logs:**
   ```bash
   sudo journalctl -u kubelet -n 100 --no-pager
   ```

2. **Common issues:**

   **Missing CNI:**
   ```
   Failed to create pod sandbox: NetworkPlugin cni failed
   ```
   Solution: Wait for CNI plugin to deploy, or redeploy CNI

   **Certificate issues:**
   ```
   Unable to load client CA file
   ```
   Solution: Reset kubeadm and reinitialize

3. **Restart kubelet:**
   ```bash
   sudo systemctl restart kubelet
   sudo systemctl status kubelet
   ```

### CNI Plugin Issues

**Symptom:**
Pods stuck in `Pending` state or `ContainerCreating` status.

**Diagnosis:**
```bash
kubectl get pods -n kube-system
kubectl describe pod <pod-name> -n kube-system
```

**Common Issues:**

#### Nodes Stuck in NotReady State

**Symptom:**
```bash
$ kubectl get nodes
NAME        STATUS     ROLES           AGE   VERSION
k8s-node1   NotReady   control-plane   5m    v1.28.0
```

**Cause:** No CNI plugin installed (this is expected after initial deployment)

**Solution:**
Install a CNI plugin. Popular options:
- [Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/)
- [Flannel](https://github.com/flannel-io/flannel)
- [Cilium](https://docs.cilium.io/en/stable/gettingstarted/k8s-install-default/)

Follow the official installation guide for your chosen CNI, then verify nodes become Ready with `kubectl get nodes`.

#### CNI Plugin Not Ready

**Error:**
```
calico-node pods not running
```

**Solution:**
```bash
# Check Calico status
kubectl get pods -n kube-system | grep calico

# Check Calico logs
kubectl logs -n kube-system <calico-pod-name>

# Redeploy Calico
kubectl delete -f <calico-manifest>
kubectl apply -f <calico-manifest>
```

#### Wrong Pod Network CIDR

**Error:**
```
Pod CIDR doesn't match CNI configuration
```

**Solution:**
Ensure `k8s_pod_subnet` matches CNI's expected CIDR:
```yaml
k8s_pod_subnet: "10.244.0.0/16"  # For Flannel/Calico
# or
k8s_pod_subnet: "10.32.0.0/12"  # For Weave
```

## Network Issues

### DNS Resolution Fails

**Symptom:**
```bash
kubectl exec -it pod -- nslookup kubernetes.default
# Returns: server can't find kubernetes.default
```

**Solutions:**

1. **Check CoreDNS pods:**
   ```bash
   kubectl get pods -n kube-system | grep coredns
   kubectl logs -n kube-system <coredns-pod>
   ```

2. **Restart CoreDNS:**
   ```bash
   kubectl rollout restart deployment coredns -n kube-system
   ```

3. **Check kube-dns service:**
   ```bash
   kubectl get svc -n kube-system kube-dns
   ```

### Firewall Blocking Ports

**Symptom:**
```
Connection refused on port 6443
```

**Required Kubernetes Ports:**

| Port | Protocol | Purpose |
|------|----------|---------|
| 6443 | TCP | Kubernetes API server |
| 2379-2380 | TCP | etcd |
| 10250 | TCP | Kubelet API |
| 10251 | TCP | kube-scheduler |
| 10252 | TCP | kube-controller-manager |

**Solutions:**

1. **Check firewall status:**
   ```bash
   sudo firewall-cmd --list-all
   sudo ufw status
   ```

2. **Allow Kubernetes ports (firewalld):**
   ```bash
   sudo firewall-cmd --permanent --add-port=6443/tcp
   sudo firewall-cmd --permanent --add-port=2379-2380/tcp
   sudo firewall-cmd --permanent --add-port=10250/tcp
   sudo firewall-cmd --permanent --add-port=10251/tcp
   sudo firewall-cmd --permanent --add-port=10252/tcp
   sudo firewall-cmd --reload
   ```

3. **Allow Kubernetes ports (ufw):**
   ```bash
   sudo ufw allow 6443/tcp
   sudo ufw allow 2379:2380/tcp
   sudo ufw allow 10250/tcp
   ```

4. **Disable firewall (development only):**
   ```yaml
   k8s_disable_firewall: true
   ```

### SELinux Blocking Operations

**Symptom:**
```
Permission denied (SELinux is enforcing)
```

**Solutions:**

1. **Check SELinux status:**
   ```bash
   sestatus
   getenforce
   ```

2. **Set to permissive (temporary):**
   ```bash
   sudo setenforce 0
   ```

3. **Disable permanently:**
   ```yaml
   # In playbook
   k8s_selinux_state: disabled
   ```

4. **Check audit logs:**
   ```bash
   sudo ausearch -m avc -ts recent
   ```

## Post-Deployment Issues

### kubectl Command Not Found

**Symptom:**
```bash
kubectl: command not found
```

**Solutions:**

1. **Verify installation:**
   ```bash
   which kubectl
   ls -la /usr/bin/kubectl
   ```

2. **Add to PATH:**
   ```bash
   export PATH=$PATH:/usr/bin
   echo 'export PATH=$PATH:/usr/bin' >> ~/.bashrc
   ```

3. **Use full path:**
   ```bash
   /usr/bin/kubectl get nodes
   ```

### kubeconfig Not Configured

**Symptom:**
```
The connection to the server localhost:8080 was refused
```

**Solutions:**

1. **Set KUBECONFIG:**
   ```bash
   export KUBECONFIG=/etc/kubernetes/admin.conf
   echo 'export KUBECONFIG=/etc/kubernetes/admin.conf' >> ~/.bashrc
   ```

2. **Copy to user directory:**
   ```bash
   mkdir -p $HOME/.kube
   sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
   sudo chown $(id -u):$(id -g) $HOME/.kube/config
   ```

### Pods Stay in Pending State

**Symptom:**
```
NAME                     READY   STATUS    RESTARTS   AGE
my-pod                   0/1     Pending   0          5m
```

**Solutions:**

1. **Describe the pod:**
   ```bash
   kubectl describe pod <pod-name>
   ```

2. **Common causes:**

   **Insufficient resources:**
   ```
   0/1 nodes are available: 1 Insufficient cpu
   ```
   Solution: Reduce resource requests or add more nodes

   **CNI not ready:**
   ```
   network not ready: NetworkReady=false
   ```
   Solution: Wait for CNI pods to be Running

   **Image pull failure:**
   ```
   Failed to pull image
   ```
   Solution: Check registry connectivity

3. **Check node conditions:**
   ```bash
   kubectl describe node <node-name>
   ```

### Services Not Accessible

**Symptom:**
Cannot access services via NodePort or ClusterIP.

**Solutions:**

1. **Check service:**
   ```bash
   kubectl get svc
   kubectl describe svc <service-name>
   ```

2. **Verify endpoints:**
   ```bash
   kubectl get endpoints <service-name>
   ```

3. **Test from within cluster:**
   ```bash
   kubectl run test --image=busybox -it --rm --restart=Never -- wget -O- <service-name>
   ```

4. **Check kube-proxy:**
   ```bash
   kubectl get pods -n kube-system | grep kube-proxy
   kubectl logs -n kube-system <kube-proxy-pod>
   ```

## Debugging Tips

### Increase Ansible Verbosity

```bash
# Minimal verbosity
ansible-playbook deploy.yml -v

# Medium verbosity (recommended for troubleshooting)
ansible-playbook deploy.yml -vv

# Maximum verbosity (shows all details)
ansible-playbook deploy.yml -vvv
```

### Enable Debug Logging

**For Kubernetes components:**

Edit `/var/lib/kubelet/kubeadm-flags.env`:
```
KUBELET_KUBEADM_ARGS="--v=4"  # 0-10, higher = more verbose
```

Restart kubelet:
```bash
sudo systemctl restart kubelet
```

### Check Systemd Services

**Container runtime:**
```bash
sudo systemctl status containerd
sudo journalctl -u containerd -f
```

**Kubelet:**
```bash
sudo systemctl status kubelet
sudo journalctl -u kubelet -f
```

**All Kubernetes services:**
```bash
sudo systemctl list-units | grep kube
```

### Validate Configurations

**Container runtime config:**
```bash
# containerd
sudo containerd config dump

# CRI-O
sudo cat /etc/crio/crio.conf
```

**Kubernetes config:**
```bash
kubectl cluster-info
kubectl get componentstatuses
kubectl get nodes -o wide
```

**Network connectivity:**
```bash
kubectl run test-$RANDOM --image=busybox -it --rm -- \
  sh -c "wget -O- https://registry.k8s.io"
```

### Collect Diagnostic Information

**System info:**
```bash
# OS and kernel
uname -a
cat /etc/os-release

# Resources
free -h
df -h
lscpu
```

**Kubernetes diagnostics:**
```bash
# Cluster info
kubectl cluster-info dump > cluster-dump.txt

# Pod logs
kubectl logs -n kube-system --tail=100 -l app=<component>

# Events
kubectl get events --all-namespaces --sort-by='.lastTimestamp'
```

**Network diagnostics:**
```bash
# Routes
ip route

# Interfaces
ip addr

# DNS
cat /etc/resolv.conf
```

## Common Error Messages

### "unable to recognize ... no matches for kind"

**Cause:** Kubernetes version mismatch or API not available

**Solution:**
```bash
kubectl api-resources  # Check available resources
kubectl version  # Check server version
```

### "connection refused" to API server

**Causes:**
- API server not running
- Firewall blocking port 6443
- Wrong kubeconfig

**Solution:**
```bash
sudo systemctl status kube-apiserver
sudo netstat -tuln | grep 6443
cat ~/.kube/config
```

### "certificate has expired or is not yet valid"

**Cause:** System time incorrect or certificates expired

**Solution:**
```bash
# Check system time
date
timedatectl

# Sync time
sudo ntpdate -s time.nist.gov

# Regenerate certificates
sudo kubeadm certs renew all
```

## Getting Further Help

### Before Asking for Help

Gather this information:

1. **Environment details:**
   - OS and version (`cat /etc/os-release`)
   - Kernel version (`uname -r`)
   - Ansible version (`ansible --version`)
   - Collection version (`ansible-galaxy collection list`)

2. **Configuration:**
   - Playbook content (sanitized)
   - Relevant variables
   - Inventory file

3. **Error output:**
   - Full Ansible error message
   - Relevant logs (`journalctl` output)
   - kubectl describe output

4. **Steps to reproduce:**
   - What command was run
   - What was expected
   - What actually happened

### Support Channels

- **GitHub Issues**: For bugs and feature requests
- **Ansible Documentation**: https://docs.ansible.com
- **Kubernetes Documentation**: https://kubernetes.io/docs/

### Useful Resources

**Kubernetes:**
- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)

**Container Runtimes:**
- [containerd Documentation](https://containerd.io/docs/)
- [CRI-O Troubleshooting](https://github.com/cri-o/cri-o/blob/main/tutorials/troubleshooting.md)

**Ansible:**
- [Ansible Debugging](https://docs.ansible.com/ansible/latest/user_guide/playbooks_debugger.html)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)

## Quick Reference

### Reset and Start Fresh

If you need to completely reset and start over:

```bash
# On target node
sudo kubeadm reset -f
sudo systemctl stop kubelet
sudo systemctl stop containerd  # or crio
sudo rm -rf /etc/kubernetes/
sudo rm -rf /var/lib/kubelet/
sudo rm -rf /var/lib/etcd/
sudo rm -rf ~/.kube/

# Then re-run playbook
ansible-playbook deploy.yml
```

### Verify Cluster Health

```bash
# All nodes ready
kubectl get nodes

# All system pods running
kubectl get pods -n kube-system

# All components healthy
kubectl get componentstatuses

# Cluster info
kubectl cluster-info
```

For more troubleshooting help, see:
- [Getting Started Guide](getting-started.md)
- [Configuration Reference](configuration-reference.md)
- [Architecture Overview](architecture.md)
