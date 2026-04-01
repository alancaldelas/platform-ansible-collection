# Documentation Index

Welcome to the documentation for the `alancaldelas.kubernetes_baremetal` Ansible collection. This collection provides automated deployment of Kubernetes clusters and container runtimes on bare-metal infrastructure.

## Quick Links

- **New to this collection?** Start with [Getting Started](getting-started.md)
- **Need configuration details?** Check the [Configuration Reference](configuration-reference.md)
- **Planning a production deployment?** Read the [Production Deployment Guide](production-deployment.md)
- **Experiencing issues?** See the [Troubleshooting Guide](troubleshooting.md)
- **Want to understand internals?** Review the [Architecture Overview](architecture.md)

## Documentation Structure

### 1. [Getting Started](getting-started.md)

Your first steps with the collection:
- Prerequisites and requirements
- Installation instructions
- Quick start examples
- Common first-time issues
- Where to get help

**Audience:** New users, developers, operators

**Time to complete:** 15-30 minutes

### 2. [Configuration Reference](configuration-reference.md)

Comprehensive variable and configuration documentation:
- Container runtime variables
- Kubernetes configuration options
- Network configuration
- System requirements
- CNI plugin options
- Complete example configurations

**Audience:** All users

**Use case:** Reference while writing playbooks

### 3. [Production Deployment Guide](production-deployment.md)

Best practices for production environments:
- Pre-deployment planning
- Capacity planning and sizing
- Security hardening
- Single-node limitations
- Network design
- Storage considerations
- Monitoring and logging
- Backup and disaster recovery
- Maintenance and upgrades

**Audience:** Operations teams, system architects

**Use case:** Planning and executing production deployments

### 4. [Troubleshooting Guide](troubleshooting.md)

Solutions to common problems:
- General Ansible issues
- Container runtime issues
- Kubernetes deployment problems
- Network problems
- Post-deployment issues
- Debugging tips
- Diagnostic procedures

**Audience:** All users, support teams

**Use case:** Resolving deployment issues

### 5. [Architecture Overview](architecture.md)

Technical deep-dive into the collection:
- Collection structure
- Role architecture and dependencies
- Deployment model (SSH-based)
- Design patterns
- Container runtime integration
- Kubernetes deployment patterns
- Extensibility guide
- Performance considerations

**Audience:** Advanced users, contributors, developers

**Use case:** Understanding internals, extending functionality

## Document Conventions

### Code Blocks

**YAML Configuration:**
```yaml
container_runtime: containerd
kubernetes_version: "1.28.0"
```

**Shell Commands:**
```bash
ansible-playbook -i inventory playbook.yml
```

**File Paths:**
```
/home/user/ansible/inventory
```

### Icons and Indicators

- ✅ **Recommended:** Best practice approach
- ⚠️ **Warning:** Important consideration
- ❌ **Not Recommended:** Anti-pattern
- 💡 **Tip:** Helpful hint
- 🔒 **Security:** Security-related information

### Variable Notation

- `variable_name`: Required variable
- `[variable_name]`: Optional variable
- `{{ variable_name }}`: Ansible variable syntax

## Documentation by Use Case

### I want to...

#### Deploy a Development Kubernetes Cluster
1. Read: [Getting Started - Example 2](getting-started.md#example-2-deploy-single-master-kubernetes-cluster)
2. Review: [Configuration Reference - Kubernetes Variables](configuration-reference.md#kubernetes-variables)
3. Execute: Run the playbook
4. If issues: [Troubleshooting - Kubernetes Deployment Issues](troubleshooting.md#kubernetes-deployment-issues)

#### Deploy Production Kubernetes
1. Read: [Production Deployment Guide](production-deployment.md)
2. Plan: Follow the pre-deployment checklist
3. Review: [Configuration Reference - Kubernetes Variables](configuration-reference.md#kubernetes-variables)
4. Execute: Deploy your cluster
5. Validate: [Production Deployment - Post-Deployment Validation](production-deployment.md#post-deployment-validation)

#### Troubleshoot a Failed Installation
1. Identify: Which component failed?
2. Check: [Troubleshooting Guide](troubleshooting.md) for relevant section
3. Debug: Follow diagnostic procedures
4. Escalate: If unresolved, collect diagnostic information

#### Customize the Collection
1. Understand: [Architecture Overview](architecture.md)
2. Review: [Extensibility](architecture.md#extensibility) section
3. Implement: Your customizations
4. Test: Validate changes

#### Setup Monitoring and Backups
1. Read: [Production Deployment - Monitoring and Logging](production-deployment.md#monitoring-and-logging)
2. Review: [Production Deployment - Backup and Disaster Recovery](production-deployment.md#backup-and-disaster-recovery)
3. Implement: Monitoring and backup solutions

## Additional Resources

### Ansible Documentation
- [Ansible User Guide](https://docs.ansible.com/ansible/latest/user_guide/index.html)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Ansible Galaxy](https://galaxy.ansible.com/)

### Kubernetes Resources
- [Official Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes API Reference](https://kubernetes.io/docs/reference/kubernetes-api/)
- [kubeadm Documentation](https://kubernetes.io/docs/reference/setup-tools/kubeadm/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

### Container Runtimes
- [containerd Documentation](https://containerd.io/docs/)
- [CRI-O Documentation](https://cri-o.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Podman Documentation](https://docs.podman.io/)

### Bare-Metal and Hardware
- [Redfish API Specification](https://www.dmtf.org/standards/redfish)
- [Dell iDRAC Documentation](https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v3.x-series)
- [HPE iLO Documentation](https://www.hpe.com/us/en/servers/integrated-lights-out-ilo.html)

## Collection Information

**Namespace:** alancaldelas
**Name:** kubernetes_baremetal
**Version:** 1.0.0

**Author:** Alan Caldelas (ajcaldelas@gmail.com)

## Support and Community

### Getting Help

1. **Documentation:** Start here - you're already in the right place!
2. **README:** Check the [main README](../README.md) for quick reference
3. **Role Documentation:** Each role has its own README:
   - [runtime](../roles/runtime/README.md) - Container runtime installation and configuration
   - [k8s](../roles/k8s/README.md) - Kubernetes cluster deployment

### Reporting Issues

When reporting issues, please include:

1. **Environment Information:**
   - Ansible version (`ansible --version`)
   - Collection version
   - Target OS and version
   - Python version

2. **Problem Description:**
   - What were you trying to do?
   - What happened instead?
   - Complete error messages

3. **Reproduction Steps:**
   - Minimal playbook to reproduce
   - Relevant variable configurations (sanitized)
   - Any modifications made to the collection

4. **Logs and Diagnostics:**
   - Ansible output with `-vvv`
   - System logs (`journalctl` output)
   - Configuration files (sanitized)

### Contributing

Contributions are welcome! Please:

1. Follow Ansible best practices
2. Test on all supported OS families
3. Update documentation for new features
4. Ensure backward compatibility
5. Add examples for new functionality

## Documentation Maintenance

### Document Version
These docs are current as of collection version **1.0.0**.

### Last Updated
February 2026

### Feedback
Found an error or have a suggestion? Please open an issue in the repository.

---

## Quick Reference Card

### Essential Commands

```bash
# Install collection
ansible-galaxy collection install alancaldelas.kubernetes_baremetal

# List collection content
ansible-galaxy collection list

# Run with verbosity
ansible-playbook -vvv playbook.yml

# Check syntax
ansible-playbook --syntax-check playbook.yml

# Dry run
ansible-playbook --check playbook.yml
```

### Essential Variables

```yaml
# Runtime
container_runtime: containerd
container_runtime_version: "1.7.2"

# Kubernetes
kubernetes_version: "1.28.0"
k8s_cluster_name: "my-cluster"
```

### Key File Locations

```
Collection:     ~/.ansible/collections/ansible_collections/alancaldelas/kubernetes_baremetal/
Docs:           <collection>/docs/
Roles:          <collection>/roles/
Examples:       <collection>/playbooks/
```

### Important Ports

```
Kubernetes:
  6443  - API Server
  2379  - etcd client
  2380  - etcd peer
  10250 - kubelet
  30000-32767 - NodePort Services
```

---

**Happy Deploying! 🚀**

For questions or support, refer to the documentation sections above or reach out to the project maintainers.
