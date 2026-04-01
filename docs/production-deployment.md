# Production Deployment Guide

Best practices and recommendations for deploying single-node Kubernetes clusters in production environments using the `alancaldelas.kubernetes_baremetal` collection.

## Important Limitations

**This collection deploys single-node Kubernetes clusters only.** Before using this for production, understand the limitations:

- **No High Availability**: Single point of failure
- **No Redundancy**: Control plane and workloads on one node
- **Limited Scalability**: Cannot scale horizontally
- **Maintenance Challenges**: Downtime required for upgrades

**Recommended Use Cases:**
- Edge computing deployments
- Branch office installations
- Development/staging environments
- Small-scale applications with acceptable downtime
- Cost-constrained environments

**Not Recommended For:**
- Mission-critical applications requiring 99.9%+ uptime
- Applications requiring horizontal scaling
- Environments requiring multi-node HA

## Table of Contents

- [Pre-Deployment Planning](#pre-deployment-planning)
- [Hardware Requirements](#hardware-requirements)
- [Network Configuration](#network-configuration)
- [Security Hardening](#security-hardening)
- [Production Configuration](#production-configuration)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Monitoring and Logging](#monitoring-and-logging)
- [Maintenance and Upgrades](#maintenance-and-upgrades)
- [Troubleshooting Production Issues](#troubleshooting-production-issues)

## Pre-Deployment Planning

### Capacity Planning

**Assess your workload requirements:**

1. **CPU Requirements**
   - Count total vCPUs needed for workloads
   - Add 2-4 vCPUs for Kubernetes system components
   - Add 20% buffer for spikes
   - **Minimum for production**: 4 vCPUs

2. **Memory Requirements**
   - Sum memory needed for all pods
   - Add 2-4 GB for Kubernetes system components
   - Add 20% buffer
   - **Minimum for production**: 8 GB RAM

3. **Storage Requirements**
   - OS: 20 GB minimum
   - Container images: 10-50 GB
   - Persistent volumes: Based on application needs
   - Logs: 10-20 GB
   - **Minimum for production**: 100 GB

**Example Production Server:**
- 8 vCPUs
- 16 GB RAM
- 200 GB SSD storage
- 1 Gbps network
- Redundant power supplies
- Hardware RAID for disk redundancy

### Environment Preparation Checklist

- [ ] Server meets minimum hardware requirements
- [ ] Supported OS installed and updated (Ubuntu 22.04 LTS recommended)
- [ ] Static IP configured or DHCP reservation set
- [ ] DNS hostname configured
- [ ] NTP/time synchronization configured
- [ ] SSH key-based authentication configured
- [ ] Firewall rules documented
- [ ] Backup solution identified
- [ ] Monitoring tools selected
- [ ] Disaster recovery plan documented

## Hardware Requirements

### Production-Grade Hardware

**Minimum Specifications:**
```yaml
CPU: 4 cores (8 recommended)
RAM: 8 GB (16 GB recommended)
Disk: 100 GB SSD (200 GB recommended)
Network: 1 Gbps
```

**Recommended Server Specifications:**
- **CPU**: Intel Xeon or AMD EPYC, 8+ cores
- **RAM**: 16-32 GB ECC memory
- **Storage**:
  - 200 GB+ NVMe SSD for OS and containers
  - Separate disk/partition for persistent volumes
  - RAID 1 or RAID 10 for redundancy
- **Network**: Dual 1 Gbps NICs for redundancy
- **Power**: Redundant power supplies

### Storage Configuration

**Production storage layout:**
```
/dev/sda1       50 GB    /             (OS)
/dev/sda2       50 GB    /var          (Docker/containerd data)
/dev/sda3       100 GB   /var/lib/kubernetes (Kubernetes data)
/dev/sdb1       500 GB   /mnt/storage  (Persistent volumes)
```

**Storage best practices:**
- Use SSDs for Kubernetes and container storage
- Separate OS from container storage
- Use LVM for flexible partitioning
- Enable TRIM for SSDs
- Monitor disk I/O and latency

## Network Configuration

### Production Network Setup

**Network Requirements:**
- Static IP address (required)
- Properly configured DNS
- NTP time synchronization
- Low latency to container registries

**DNS Configuration:**
```
# /etc/hosts
127.0.0.1       localhost
192.168.1.100   k8s-prod.company.com k8s-prod

# /etc/resolv.conf
nameserver 192.168.1.1
search company.com
```

### Firewall Configuration

**Required Kubernetes Ports:**

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Admin Network | SSH |
| 6443 | TCP | Admin Network / Application Clients | Kubernetes API |
| 2379-2380 | TCP | Localhost | etcd |
| 10250 | TCP | Localhost | Kubelet API |
| 10251 | TCP | Localhost | kube-scheduler |
| 10252 | TCP | Localhost | kube-controller-manager |
| 30000-32767 | TCP | Application Clients | NodePort Services |

**Firewall Rules (firewalld example):**
```bash
# SSH
firewall-cmd --permanent --add-port=22/tcp

# Kubernetes API
firewall-cmd --permanent --add-port=6443/tcp

# NodePort range
firewall-cmd --permanent --add-port=30000-32767/tcp

firewall-cmd --reload
```

### Load Balancer / Proxy

For production access, consider placing the node behind a load balancer:

```
Internet → Load Balancer (HAProxy/Nginx) → Kubernetes Node
```

Benefits:
- SSL/TLS termination
- Rate limiting
- Access logging
- Easier maintenance (can swap nodes)

## Security Hardening

### Operating System Hardening

**Security checklist:**
- [ ] Disable unused services
- [ ] Configure automatic security updates
- [ ] Enable firewall
- [ ] Disable root SSH login
- [ ] Use SSH keys only (disable password auth)
- [ ] Configure fail2ban
- [ ] Enable audit logging
- [ ] Apply CIS benchmarks

**Example hardening:**
```bash
# Disable password authentication
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Restart SSH
sudo systemctl restart sshd

# Enable automatic security updates (Ubuntu)
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Kubernetes Security

**Security best practices:**

1. **RBAC (Role-Based Access Control)**
   ```yaml
   # Enable RBAC (enabled by default in modern k8s)
   # Create service accounts for applications
   # Use principle of least privilege
   ```

2. **Pod Security Standards**
   ```yaml
   # Enforce pod security policies
   apiVersion: policy/v1beta1
   kind: PodSecurityPolicy
   metadata:
     name: restricted
   spec:
     privileged: false
     allowPrivilegeEscalation: false
     runAsUser:
       rule: MustRunAsNonRoot
   ```

3. **Network Policies**
   ```yaml
   # Restrict pod-to-pod communication
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

4. **Secrets Management**
   - Use Kubernetes secrets (never plain environment variables)
   - Consider external secret management (Vault, Sealed Secrets)
   - Encrypt secrets at rest

5. **Image Security**
   - Use trusted registries only
   - Scan images for vulnerabilities
   - Use specific image tags (not `latest`)
   - Implement image pull policies

### SELinux Configuration

**For production (RHEL/CentOS):**
```yaml
k8s_selinux_state: enforcing  # Don't disable in production
```

Configure SELinux contexts properly rather than disabling.

## Production Configuration

### Recommended Production Variables

```yaml
---
# Production Kubernetes deployment

# Cluster identification
k8s_cluster_name: production

# Kubernetes version (pinned)
kubernetes_version: "1.28.0"

# Container runtime
k8s_container_runtime: containerd
k8s_manage_container_runtime: true
container_runtime_version: "1.7.2"
containerd_build_method: binary

# Registry configuration
container_registries:
  - registry.k8s.io
  - quay.io
  - harbor.company.com  # Private registry

# Storage configuration
container_storage_path: /var/lib/containerd
container_log_max_size: "100Mi"
container_log_max_files: 10

# Network configuration
k8s_pod_subnet: "10.244.0.0/16"
k8s_service_subnet: "10.96.0.0/12"
# CNI must be installed manually post-deployment (recommend Calico for production)

# System requirements (strict)
k8s_min_cpu_cores: 4
k8s_min_memory_mb: 8192
k8s_min_disk_space_gb: 100
k8s_check_network_connectivity: true

# Security (production settings)
k8s_selinux_state: enforcing  # Or disabled if not RHEL/CentOS
k8s_disable_firewall: false  # Keep firewall enabled

# Source installation (not recommended for production)
k8s_install_from_source: false
```

### Production Playbook Example

```yaml
---
- name: Deploy Production Kubernetes Cluster
  hosts: production_k8s
  become: yes
  vars_files:
    - vars/production.yml
    - vars/secrets.yml  # Encrypted with ansible-vault

  pre_tasks:
    - name: Verify production checklist
      assert:
        that:
          - ansible_memtotal_mb >= 8192
          - ansible_processor_vcpus >= 4
          - k8s_cluster_name is defined
        fail_msg: "Production requirements not met"

  roles:
    - alancaldelas.kubernetes_baremetal.k8s

  post_tasks:
    - name: Verify cluster health
      command: kubectl get nodes
      register: nodes
      failed_when: "'Ready' not in nodes.stdout"
```

## Backup and Disaster Recovery

### What to Backup

**Critical data:**
1. **etcd database** - Cluster state
2. **Kubernetes manifests** - Application deployments
3. **Persistent volumes** - Application data
4. **Certificates** - Cluster certificates
5. **Configuration files** - Ansible playbooks, vars

### Backup etcd

**Backup script:**
```bash
#!/bin/bash
# backup-etcd.sh

BACKUP_DIR="/backup/etcd"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup etcd
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save $BACKUP_DIR/etcd-snapshot-$DATE.db

# Keep only last 7 backups
ls -t $BACKUP_DIR/etcd-snapshot-*.db | tail -n +8 | xargs rm -f
```

**Schedule with cron:**
```bash
# Daily at 2 AM
0 2 * * * /usr/local/bin/backup-etcd.sh
```

### Restore etcd

```bash
# Stop Kubernetes components
systemctl stop kubelet

# Restore snapshot
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd/etcd-snapshot-DATE.db \
  --data-dir=/var/lib/etcd-restore

# Update etcd data directory
mv /var/lib/etcd /var/lib/etcd.old
mv /var/lib/etcd-restore /var/lib/etcd

# Start Kubernetes
systemctl start kubelet
```

### Backup Kubernetes Resources

```bash
#!/bin/bash
# backup-k8s-resources.sh

BACKUP_DIR="/backup/kubernetes"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR/$DATE

# Backup all namespaces
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get all,cm,secret,pvc -n $ns -o yaml > $BACKUP_DIR/$DATE/$ns.yaml
done

# Backup cluster-wide resources
kubectl get clusterrole,clusterrolebinding,sc,pv -o yaml > $BACKUP_DIR/$DATE/cluster.yaml
```

### Disaster Recovery Plan

**Recovery steps:**

1. **Rebuild server** with same OS and IP
2. **Run Ansible playbook** to reinstall Kubernetes
3. **Restore etcd** from backup
4. **Restore certificates** if needed
5. **Redeploy applications** from manifests
6. **Restore persistent data** from backup
7. **Verify cluster health**

**Recovery Time Objective (RTO):**
- Server rebuild: 30-60 minutes
- Kubernetes reinstall: 10-20 minutes
- Data restore: Variable (depends on data size)
- **Total: 1-3 hours**

## Monitoring and Logging

### Monitoring Setup

**Recommended monitoring stack:**

1. **Prometheus** - Metrics collection
2. **Grafana** - Visualization
3. **Node Exporter** - System metrics
4. **kube-state-metrics** - Kubernetes metrics

**Quick install:**
```bash
# Using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack
```

**Key metrics to monitor:**
- Node CPU/memory/disk usage
- Pod CPU/memory usage
- etcd latency
- API server latency
- Container restart count
- Disk I/O

### Logging Setup

**Recommended logging:**

1. **Container logs** - kubectl logs
2. **System logs** - journalctl
3. **Audit logs** - Kubernetes audit logging

**Centralized logging (optional):**
```bash
# EFK Stack (Elasticsearch, Fluentd, Kibana)
# or
# Loki + Grafana
```

**Enable audit logging:**
```yaml
# In kubeadm config
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
apiServer:
  extraArgs:
    audit-log-path: /var/log/kubernetes/audit.log
    audit-log-maxage: "30"
    audit-log-maxbackup: "10"
    audit-log-maxsize: "100"
```

### Alerting

**Critical alerts:**
- Node down
- Disk space >85%
- Memory usage >90%
- etcd unhealthy
- Persistent pod failures
- Certificate expiration (30 days)

## Maintenance and Upgrades

### Upgrade Planning

**Upgrade strategy for single-node:**
1. **Requires downtime** - no way around it
2. **Test in staging first**
3. **Backup before upgrade**
4. **Have rollback plan**
5. **Schedule during maintenance window**

### Kubernetes Version Upgrades

**Safe upgrade path:**
- Only upgrade one minor version at a time
- Example: 1.27 → 1.28 → 1.29 (not 1.27 → 1.29)

**Upgrade procedure:**

1. **Backup everything**
   ```bash
   /usr/local/bin/backup-etcd.sh
   /usr/local/bin/backup-k8s-resources.sh
   ```

2. **Update playbook variables**
   ```yaml
   kubernetes_version: "1.29.0"  # New version
   ```

3. **Run upgrade playbook**
   ```bash
   ansible-playbook upgrade.yml --check  # Dry run
   ansible-playbook upgrade.yml
   ```

4. **Verify upgrade**
   ```bash
   kubectl get nodes
   kubectl version
   kubectl get pods -A
   ```

5. **Update cluster components**
   ```bash
   kubectl get pods -n kube-system
   # Restart deployments if needed
   kubectl rollout restart deployment -n kube-system coredns
   ```

### Container Runtime Updates

```bash
# Update via Ansible
ansible-playbook upgrade-runtime.yml

# Or manually
sudo systemctl stop kubelet
sudo systemctl stop containerd
# Update containerd binary
sudo systemctl start containerd
sudo systemctl start kubelet
```

## Troubleshooting Production Issues

### Performance Issues

**Symptom:** Slow pod scheduling or API responsiveness

**Diagnosis:**
```bash
# Check node resources
kubectl top node
kubectl describe node

# Check API server
kubectl get --raw /metrics | grep apiserver

# Check etcd
ETCDCTL_API=3 etcdctl endpoint health
```

**Solutions:**
- Increase node resources
- Reduce workload
- Optimize resource requests/limits

### Disk Space Issues

**Monitor disk usage:**
```bash
df -h
du -sh /var/lib/containerd/*
du -sh /var/lib/kubelet/*
```

**Clean up:**
```bash
# Remove unused images
crictl rmi --prune

# Remove unused containers
crictl rm $(crictl ps -a -q)

# Clean up logs
journalctl --vacuum-time=7d
```

### Certificate Expiration

**Check certificate expiration:**
```bash
kubeadm certs check-expiration
```

**Renew certificates:**
```bash
sudo kubeadm certs renew all
sudo systemctl restart kubelet
```

## Production Checklist

### Pre-Deployment
- [ ] Hardware meets production specifications
- [ ] Static IP configured
- [ ] DNS properly configured
- [ ] NTP synchronized
- [ ] Firewall rules configured
- [ ] SSH key authentication configured
- [ ] OS security hardening complete
- [ ] Backup solution tested
- [ ] Monitoring configured
- [ ] Documentation complete

### Post-Deployment
- [ ] Cluster health verified
- [ ] All pods running
- [ ] CNI functioning
- [ ] DNS resolution working
- [ ] Application deployed and tested
- [ ] Backups working
- [ ] Monitoring collecting metrics
- [ ] Alerts configured
- [ ] Disaster recovery plan documented
- [ ] Team trained on operations

### Ongoing Maintenance
- [ ] Daily: Check cluster health
- [ ] Weekly: Review metrics and logs
- [ ] Monthly: Test backups and recovery
- [ ] Quarterly: Security updates
- [ ] Annually: Kubernetes version upgrade

## Additional Resources

- [Kubernetes Production Best Practices](https://kubernetes.io/docs/setup/best-practices/)
- [CIS Kubernetes Benchmarks](https://www.cisecurity.org/benchmark/kubernetes)
- [Production-Grade Container Orchestration](https://kubernetes.io/docs/setup/production-environment/)

For more information:
- [Getting Started Guide](getting-started.md)
- [Configuration Reference](configuration-reference.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Architecture Overview](architecture.md)
