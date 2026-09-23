import pathlib
import re
import unittest

import yaml


ROLE = pathlib.Path(__file__).resolve().parents[2] / 'roles/k8s_uninstall'


class RoleTests(unittest.TestCase):
    def test_repo_cleanup_preserves_google_cloud_sdk(self):
        tasks = yaml.safe_load((ROLE / 'tasks/remove.yml').read_text())
        task = next(task for task in tasks if 'ansible.builtin.lineinfile' in task)
        pattern = task['ansible.builtin.lineinfile']['regexp']
        self.assertRegex('deb https://packages.cloud.google.com/apt kubernetes-xenial main', pattern)
        self.assertRegex('deb [arch=amd64] https://download.docker.com/linux/ubuntu noble stable', pattern)
        self.assertIsNone(re.search(pattern, 'deb https://packages.cloud.google.com/apt cloud-sdk main'))
        self.assertIsNone(re.search(pattern, 'deb https://example.com/linux stable main'))

    def test_socket_types_are_passed_as_one_systemctl_argument(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        task = next(task for task in tasks if task.get('ansible.builtin.command', {}).get('argv', [None])[0] == 'systemctl')
        self.assertIn('--type=service,socket', task['ansible.builtin.command']['argv'])

    def test_not_found_placeholder_units_are_never_stopped(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        task = next(task for task in tasks if '_uninstall_services' in task.get('ansible.builtin.set_fact', {}))
        expression = task['ansible.builtin.set_fact']['_uninstall_services']
        self.assertIn("rejectattr('value.status', 'equalto', 'not-found')", expression)
