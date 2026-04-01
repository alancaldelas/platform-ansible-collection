# Common Prerequisites Role

This Ansible role provides common system prerequisites and configuration tasks shared across the kubernetes_baremetal collection. It handles foundational system setup that other roles depend on.

## Purpose

The `common_prereqs` role is designed to be included by other roles to ensure common system requirements are met before deploying container runtimes or Kubernetes components.

## Features

- Common package installation across distributions
- Basic system configuration
- Network prerequisites
- Shared utility tasks

## Requirements

- Ansible 2.9+
- Target systems: Linux (Debian/Ubuntu, RHEL/CentOS/Fedora)
- Root or sudo access

## Role Variables

This role currently inherits variables from the calling role and does not define its own default variables.

## Dependencies

None - this is a foundational role.

## Example Usage

### Include in Another Role

```yaml
---
# In another role's tasks/main.yml
- name: Setup common prerequisites
  include_role:
    name: alancaldelas.kubernetes_baremetal.common_prereqs
```

### Standalone Playbook

```yaml
---
- name: Setup common system prerequisites
  hosts: all
  become: yes
  roles:
    - alancaldelas.kubernetes_baremetal.common_prereqs
```

## Architecture

### File Structure
```
common_prereqs/
├── defaults/main.yml    # Default variables (currently empty)
├── tasks/
│   └── main.yml        # Main task file
├── vars/main.yml       # Internal variables
└── handlers/main.yml   # Event handlers
```

## Future Enhancements

This role is designed to be extended with common tasks such as:
- Time synchronization setup (chrony/ntp)
- DNS configuration validation
- Common logging setup
- Security hardening tasks
- System update management

## License

MIT-0

## Author Information

Part of the kubernetes_baremetal collection.

Created by Alan Caldelas (ajcaldelas@gmail.com)
