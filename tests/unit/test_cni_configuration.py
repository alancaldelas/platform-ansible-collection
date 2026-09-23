import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(path):
    return yaml.safe_load((ROOT / path).read_text())


class CiliumConfigurationTests(unittest.TestCase):
    def test_base_flags_pin_kubeadm_assigned_pod_cidr(self):
        for role in ('k8s', 'cluster_upgrade'):
            defaults = load('roles/%s/defaults/main.yml' % role)
            self.assertEqual(defaults['cilium_ipam_mode'], 'kubernetes', role)
            self.assertIn('ipam.mode={{ cilium_ipam_mode }}', defaults['cilium_base_flags'], role)

    def test_every_cilium_command_carries_the_base_flags(self):
        commands = []
        for task in load('roles/k8s/tasks/cni_install.yml') + load('roles/cluster_upgrade/tasks/upgrade_cilium.yml'):
            command = task.get('command') or task.get('ansible.builtin.command') or ''
            if isinstance(command, str) and '/usr/local/bin/cilium' in command and (
                    ' install ' in command or ' upgrade ' in command):
                commands.append((task['name'], command))
        self.assertEqual(len(commands), 4, [name for name, _ in commands])
        for name, command in commands:
            self.assertIn('{{ cilium_base_flags }}', command, name)

    def test_multus_is_installed_by_default(self):
        defaults = load('roles/k8s/defaults/main.yml')
        self.assertIs(defaults['k8s_multus_enabled'], True)
        tasks = load('roles/k8s/tasks/cni_install.yml')
        install = next(task for task in tasks if task['name'] == 'Install Multus CNI')
        self.assertIn('k8s_multus_enabled | bool', install['when'])

    def test_cilium_leaves_cni_directory_shared_when_multus_is_enabled(self):
        for role in ('k8s', 'cluster_upgrade'):
            flags = load('roles/%s/defaults/main.yml' % role)['cilium_base_flags']
            self.assertIn('cni.exclusive=false', flags, role)
            self.assertIn('k8s_multus_enabled', flags, role)
