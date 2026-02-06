# openshift_agent_install

Ansible role to install OpenShift clusters (SNO, Compact, or Large) using the **Agent Installer** on **baremetal** hardware.

This role focuses strictly on baremetal deployments where nodes are managed via Redfish-compatible BMCs. It handles:
1. Downloading OpenShift installer and client binaries.
2. Generating the Agent ISO image based on templates.
3. Automatically mounting the ISO to baremetal nodes via Redfish.
4. Setting the boot order to Virtual Media for the installation.

## Requirements

- Baremetal nodes with Redfish-compatible BMCs.
- `python3-redfish` (or `redfish` on RHEL) installed on the control node.
- A local HTTP server is started by the role to serve the ISO to the BMCs.

## Role Variables

### Mandatory Variables
- `pull_secret`: Your OpenShift pull secret.
- `openshift_ssh_key`: SSH public key for node access.
- `base_domain`: Base domain for the cluster (e.g., `example.com`).
- `cluster_name`: Name of the cluster.
- `machine_cidr`: The network CIDR for the cluster nodes (e.g., `192.168.1.0/24`).

### Multi-Node Mandatory Variables
If `control_plane_replicas > 1`, the following are required:
- `api_vip`: The Virtual IP for the API.
- `ingress_vip`: The Virtual IP for Ingress.

### Optional Variables
- `cluster_type`: `sno` (default), `compact`, or `large`.
- `control_plane_replicas`: Number of control plane nodes (default: `1`).
- `compute_replicas`: Number of worker nodes (default: `0`).
- `baremetal_nodes`: List of nodes with BMC and NIC details (see example below).
- `rendezvous_ip`: The IP used for initial discovery. Defaults to the first master's IP if not provided.
- `gateway_ip`: Gateway for the node network (default: `192.168.1.1`).
- `redfish_vendor_defaults`: Mapping of vendor names to Redfish resource IDs (Dell, HPE, Lenovo, Generic).

## Baremetal Node Definition Example

```yaml
baremetal_nodes:
  - hostname: master-0
    role: master
    vendor: dell  # Supported: dell, hpe, lenovo, generic
    bmc:
      address: 192.168.1.100
      username: admin
      password: password
    nics:
      - name: eth0
        mac: 00:11:22:33:44:55
        ip: 192.168.1.10/24
    install_disk: /dev/sda
```

## Supported Vendors
The role uses vendor-specific Redfish paths defined in `redfish_vendor_defaults`:
- **Dell**: `/redfish/v1/Managers/iDRAC.Embedded.1/...`
- **HPE**: `/redfish/v1/Managers/1/VirtualMedia/2/...`
- **Lenovo**: `/redfish/v1/Managers/1/VirtualMedia/1/...`
- **Generic**: Standard `/redfish/v1/Managers/1/...` paths.

## Supported Cluster Types

### 1. Single Node OpenShift (SNO)
- `control_plane_replicas: 1`
- `compute_replicas: 0`
- No VIPs required.

### 2. Compact Cluster
- `control_plane_replicas: 3`
- `compute_replicas: 0`
- `api_vip` and `ingress_vip` are **mandatory**.

### 3. Large Cluster
- `control_plane_replicas: 3`
- `compute_replicas: 2` (or more)
- `api_vip` and `ingress_vip` are **mandatory**.

## License

MIT-0
