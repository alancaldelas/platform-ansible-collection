# Runtime Role

This Ansible role installs and configures container runtime environments for Kubernetes bare-metal deployments. It supports multiple container runtimes with both binary and source installation methods.

## Supported Container Runtimes

- **containerd** - Industry-standard container runtime
- **CRI-O** - Lightweight container runtime for Kubernetes
- **Docker** - Traditional container platform
- **Podman** - Daemonless container engine

## Features

### Installation Methods
- **Binary Installation**: Download pre-built binaries (default, faster)
- **Source Installation**: Compile from source code (customizable, latest features)

### Multi-OS Support
- Debian/Ubuntu (apt-based systems)
- RHEL/CentOS/Fedora (yum/dnf-based systems)

### Container Runtime Features
- Systemd cgroup management (Kubernetes-ready)
- Custom registry configuration
- Insecure registry support
- Storage driver configuration
- Log rotation and size limits
- CNI plugin integration
- Kernel parameter optimization

### System Optimization
- Kernel parameter tuning for containers
- Required kernel modules (overlay, br_netfilter)
- Swap disabling (Kubernetes requirement)
- zswap disabling (Fedora-specific)
- Network bridge configuration

## Requirements

- Ansible 2.9+
- Target systems: Linux (Debian/Ubuntu, RHEL/CentOS/Fedora)
- Root or sudo access on target hosts
- Internet connectivity for downloading binaries/sources

## Role Variables

### Container Runtime Selection
```yaml
# Choose container runtime
container_runtime: containerd  # containerd, crio, docker, podman
container_runtime_version: "1.7.2"

# Build method for containerd and CRI-O
containerd_build_method: binary  # binary or source
crio_build_method: binary        # binary or source
```

### Version Configuration
```yaml
# Component versions
runc_version: "1.1.9"
cni_version: "1.3.0"
go_version: "1.21.3"
kubernetes_version: "1.28"
```

### Registry Configuration
```yaml
# Standard registries (HTTPS)
container_registries:
  - quay.io
  - registry.k8s.io
  - docker.io

# Insecure registries (HTTP/self-signed certs)
container_insecure_registries:
  - localhost:5000
  - registry.internal.company.com

# Registry mirrors for improved performance
container_registry_mirrors: []
```

### Storage Configuration
```yaml
container_storage_driver: overlay2
container_storage_path: /var/lib/containers
container_log_max_size: "10Mi"
container_log_max_files: 3
```

### Build Configuration (Source Installation)
```yaml
# Build directories
containerd_build_dir: /tmp/containerd-build
crio_build_dir: /tmp/crio-build

# Build dependencies (customizable per OS)
containerd_build_packages:
  - git
  - make
  - gcc
  - libc6-dev
  - pkg-config
  - libseccomp-dev
  - libbtrfs-dev

containerd_build_packages_rhel:
  - git
  - make
  - gcc
  - glibc-devel
  - pkgconfig
  - libseccomp-devel
  - btrfs-progs-devel
```

## Dependencies

This role depends on common system prerequisites that are handled by the `common_prereqs` tasks:
- Network configuration
- Basic system tools
- Kernel modules and parameters

## Example Playbooks

### Basic containerd Installation
```yaml
---
- hosts: kubernetes_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.runtime
  vars:
    container_runtime: containerd
    container_runtime_version: "1.7.2"
```

### CRI-O with Source Build
```yaml
---
- hosts: kubernetes_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.runtime
  vars:
    container_runtime: crio
    crio_build_method: source
    kubernetes_version: "1.28"
```

### Multi-Runtime with Custom Registry
```yaml
---
- hosts: kubernetes_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.runtime
  vars:
    container_runtime: containerd
    container_registries:
      - quay.io
      - registry.k8s.io
      - harbor.company.com
    container_insecure_registries:
      - localhost:5000
      - dev-registry.internal:8080
```

### Production Configuration
```yaml
---
- hosts: production_k8s
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.runtime
  vars:
    container_runtime: containerd
    container_runtime_version: "1.7.2"
    containerd_build_method: binary
    container_storage_path: /opt/containerd/storage
    container_log_max_size: "50Mi"
    container_log_max_files: 5
    container_registries:
      - registry.k8s.io
      - quay.io
      - company-registry.com
```

## Architecture

### File Structure
```
runtime/
├── defaults/main.yml           # Default variables
├── files/
│   ├── containerd.service      # containerd systemd service
│   └── crio.service           # CRI-O systemd service
├── handlers/main.yml          # Service restart handlers
├── tasks/
│   ├── main.yml              # Main task orchestration
│   ├── common.yml            # Common system setup
│   ├── containerd.yml        # containerd installation
│   ├── crio.yml              # CRI-O installation
│   ├── docker.yml            # Docker installation
│   └── podman.yml            # Podman installation
├── templates/
│   ├── containerd-config.toml.j2  # containerd configuration
│   └── crio.conf.j2              # CRI-O configuration
└── vars/main.yml             # Internal variables
```

### Task Flow
1. **Common Setup** (`common.yml`)
   - Install OS-specific packages
   - Configure kernel parameters
   - Load kernel modules
   - Disable swap/zswap
   - Install Go (for source builds)

2. **Runtime Installation** (runtime-specific `.yml`)
   - Download/build binaries
   - Install systemd services
   - Configure runtime settings
   - Start and enable services

3. **Configuration Management**
   - Generate configuration files from templates
   - Apply registry and storage settings
   - Restart services when needed

## Configuration Templates

### containerd Configuration
- **Registry mirrors**: HTTPS endpoints for standard registries
- **Insecure registries**: HTTP endpoints with TLS skip verification
- **Runtime settings**: systemd cgroups, proper pause image
- **Storage**: Configurable storage driver and paths
- **CNI integration**: Proper plugin paths and configuration

### CRI-O Configuration
- **Runtime paths**: Correct runc binary locations
- **Registry settings**: Dynamic registry and insecure registry lists
- **Storage configuration**: Configurable drivers and paths
- **Logging**: Size limits and rotation settings
- **Security**: Default capabilities and sysctls

## Advanced Usage

### Custom Build from Source
For organizations requiring custom patches or latest features:

```yaml
containerd_build_method: source
container_runtime_version: "1.7.3"  # Latest version
go_version: "1.21.4"                # Latest Go version
```

### Air-Gapped Environments
For environments without internet access:

```yaml
# Pre-stage binaries and configure local registry
container_registries:
  - local-registry.company.com
container_insecure_registries:
  - local-registry.company.com  # If using self-signed certs
```

### High-Performance Configuration
For high-throughput environments:

```yaml
container_log_max_size: "100Mi"
container_log_max_files: 10
container_storage_path: /fast-ssd/containers  # Use fast storage
```

## Troubleshooting

### Common Issues

1. **Service fails to start**
   - Check systemd logs: `journalctl -u containerd`
   - Verify binary permissions and paths
   - Ensure all dependencies are installed

2. **Registry connection issues**
   - Verify registry URLs in configuration
   - Check firewall/network connectivity
   - Confirm insecure registry settings

3. **Storage issues**
   - Check available disk space
   - Verify storage path permissions
   - Confirm storage driver compatibility

### Debug Mode
Enable verbose logging by setting debug level in runtime configuration.

## License

MIT-0

## Author Information

This role was created as part of the kubernetes_baremetal collection for automating Kubernetes deployments on bare-metal infrastructure.

## Contributing

1. Follow Ansible best practices
2. Test on all supported OS families
3. Update documentation for new features
4. Ensure backward compatibility
