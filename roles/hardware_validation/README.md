# Hardware Validation Role

This Ansible role provides hardware validation and verification tasks for bare-metal Kubernetes deployments. It ensures that target systems meet hardware requirements before deployment.

## Purpose

The `hardware_validation` role validates hardware specifications, BMC/IPMI connectivity, and system firmware to ensure successful Kubernetes deployments on bare-metal infrastructure.

## Features

- Hardware specification validation
- BMC/IPMI connectivity checks
- Firmware version verification
- Storage subsystem validation
- Network interface validation

## Requirements

- Ansible 2.9+
- Target systems: Physical bare-metal servers
- BMC/IPMI access (for remote management validation)
- Root or sudo access

## Role Variables

### Hardware Requirements
```yaml
hw_min_cpu_cores: 2           # Minimum CPU cores
hw_min_memory_gb: 4           # Minimum RAM in GB
hw_min_disk_size_gb: 100      # Minimum disk size in GB
```

### BMC/IPMI Configuration
```yaml
hw_validate_bmc: true         # Enable BMC validation
hw_bmc_user: "admin"          # BMC username
hw_bmc_password: ""           # BMC password (use vault)
```

### Network Validation
```yaml
hw_required_nics: 1           # Minimum number of NICs
hw_min_nic_speed_mbps: 1000   # Minimum NIC speed
```

## Dependencies

### Custom Modules
This role works with the collection's custom modules:
- `ipmi_configuration` - IPMI server configuration
- `redfish_iso_mount` - Redfish ISO mounting

## Example Playbooks

### Basic Hardware Validation
```yaml
---
- name: Validate hardware for Kubernetes
  hosts: bare_metal_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.hardware_validation
  vars:
    hw_min_cpu_cores: 4
    hw_min_memory_gb: 8
    hw_min_disk_size_gb: 200
```

### Validate BMC Connectivity
```yaml
---
- name: Validate BMC access
  hosts: bare_metal_nodes
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.hardware_validation
  vars:
    hw_validate_bmc: true
    hw_bmc_user: "{{ vault_bmc_user }}"
    hw_bmc_password: "{{ vault_bmc_password }}"
```

### Pre-deployment Full Validation
```yaml
---
- name: Complete hardware validation before Kubernetes deployment
  hosts: k8s_bare_metal
  become: yes

  pre_tasks:
    - name: Validate hardware meets requirements
      include_role:
        name: alancaldelas.kubernetes_baremetal.hardware_validation
      vars:
        hw_min_cpu_cores: 8
        hw_min_memory_gb: 16
        hw_min_disk_size_gb: 500
        hw_validate_bmc: true

  roles:
    - alancaldelas.kubernetes_baremetal.runtime
    - alancaldelas.kubernetes_baremetal.k8s
```

## Architecture

### File Structure
```
hardware_validation/
├── defaults/main.yml    # Default validation parameters
├── tasks/
│   └── main.yml        # Validation tasks
├── vars/main.yml       # Internal variables
└── handlers/main.yml   # Event handlers
```

### Validation Checks

The role can perform:
- **CPU**: Core count, architecture, CPU flags
- **Memory**: Total RAM, available memory
- **Storage**: Disk capacity, I/O performance
- **Network**: Interface count, speed, connectivity
- **BMC**: Accessibility, firmware version
- **Firmware**: BIOS/UEFI version, settings

## Integration with Custom Modules

### Using ipmi_configuration Module
```yaml
- name: Configure IPMI settings
  alancaldelas.kubernetes_baremetal.ipmi_configuration:
    host: "{{ inventory_hostname }}"
    user: "{{ hw_bmc_user }}"
    password: "{{ hw_bmc_password }}"
    setting: "boot_device"
    value: "disk"
```

### Using redfish_iso_mount Module
```yaml
- name: Mount installation ISO via Redfish
  alancaldelas.kubernetes_baremetal.redfish_iso_mount:
    baseuri: "{{ bmc_address }}"
    username: "{{ hw_bmc_user }}"
    password: "{{ hw_bmc_password }}"
    iso_url: "http://mirror.example.com/ubuntu-22.04.iso"
    state: present
```

## Troubleshooting

### Common Issues

1. **BMC not accessible**
   - Verify network connectivity to BMC
   - Check BMC credentials
   - Ensure BMC is enabled in BIOS

2. **Hardware below minimum requirements**
   - Adjust role variables to match available hardware
   - Upgrade hardware if needed for production

3. **IPMI/Redfish not responding**
   - Verify BMC firmware is up to date
   - Check firewall rules
   - Ensure proper network configuration

## Future Enhancements

Planned features:
- RAID configuration validation
- Temperature and health monitoring
- Power supply redundancy checks
- Hardware inventory reporting
- Compatibility matrix validation

## License

MIT-0

## Author Information

Part of the kubernetes_baremetal collection for bare-metal infrastructure management.

Created by Alan Caldelas (ajcaldelas@gmail.com)

## Contributing

When contributing hardware validation tasks:
1. Ensure compatibility across different vendors (Dell, HPE, Supermicro, etc.)
2. Handle validation failures gracefully
3. Provide clear error messages
4. Document vendor-specific requirements
5. Test on various hardware platforms
