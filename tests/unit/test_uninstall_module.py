import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

from test_uninstall import load_helper


ROOT = pathlib.Path(__file__).resolve().parents[2]
HELPER_NAME = 'ansible_collections.alancaldelas.kubernetes_baremetal.plugins.module_utils.uninstall'
sys.modules[HELPER_NAME] = load_helper()
spec = importlib.util.spec_from_file_location('uninstall_node', ROOT / 'plugins/modules/k8s_uninstall_node.py')
node = importlib.util.module_from_spec(spec)
spec.loader.exec_module(node)


class Finished(Exception):
    pass


class ModuleTests(unittest.TestCase):
    def module(self, phase='preflight', check=False):
        module = types.SimpleNamespace(params={
            'phase': phase, 'confirmation': 'REMOVE-ALL-CONTAINERS',
            'extra_data_paths': [], 'command_timeout': 120,
        }, check_mode=check, warned=[])
        module.warn = module.warned.append
        return module

    def test_unsupported_cri_still_cleans_standalone_containerd(self):
        teardown = node.Teardown(self.module('workloads'))
        calls = []
        teardown.preflight = lambda: []
        teardown.tools = {'ctr': 'ctr', 'crictl': 'crictl', 'podman': None}

        def run(args, mutation=False):
            calls.append(args)
            if args[0] == 'crictl':
                raise RuntimeError('CRI Unimplemented')
            return ''
        teardown.run = run
        with patch.object(node.os.path, 'exists', side_effect=lambda path: path == '/run/containerd/containerd.sock'):
            teardown.workloads()
        self.assertTrue(any(args[0] == 'ctr' for args in calls))
        self.assertTrue(teardown.warnings)

    def test_command_adapter_refuses_mutation_in_check_mode(self):
        teardown = node.Teardown(self.module(check=True))
        with patch.object(node.subprocess, 'run') as runner:
            with self.assertRaisesRegex(ValueError, 'check mode'):
                teardown.run(['docker', 'rm', '-f', 'x'], mutation=True)
            runner.assert_not_called()

    def test_storage_boundary_requires_explicit_custom_root(self):
        teardown = node.Teardown(self.module())
        teardown.check_storage('/var/lib/containerd/snapshots')
        with self.assertRaisesRegex(ValueError, 'Custom runtime storage'):
            teardown.check_storage('/var/lib/containerd-other')

    def test_reused_pid_is_never_tracked_as_a_container(self):
        module = self.module()
        module.params['tracked_processes'] = [{'pid': 4321, 'start': '100'}]
        teardown = node.Teardown(module)
        stat = '4321 (payload) S ' + ' '.join(['0'] * 18) + ' 200'
        with patch.object(node, 'processes', return_value=[]), patch.object(node, 'read_text', return_value=stat):
            self.assertEqual(teardown.remaining(), [])

    def test_orphaned_payload_is_still_tracked(self):
        module = self.module()
        module.params['tracked_processes'] = [{'pid': 4321, 'start': '100'}]
        teardown = node.Teardown(module)
        stat = '4321 (payload) S ' + ' '.join(['0'] * 18) + ' 100'
        with patch.object(node, 'processes', return_value=[]), patch.object(node, 'read_text', return_value=stat):
            self.assertEqual(teardown.remaining(), module.params['tracked_processes'])

    def test_leftover_executable_prevents_success(self):
        module = self.module('verify')
        module.params['verify_binaries'] = ['crun']
        teardown = node.Teardown(module)
        with patch.object(node, 'processes', return_value=[]), patch.object(node.shutil, 'which', return_value='/opt/bin/crun'):
            with self.assertRaisesRegex(ValueError, 'Executables remain'):
                teardown.verify()

    def test_check_mode_workloads_only_inspects(self):
        module = self.module('workloads', check=True)
        result = {}

        def finish(**kwargs):
            result.update(kwargs)
            raise Finished()
        module.exit_json = finish
        with patch.object(node, 'AnsibleModule', return_value=module), \
             patch.object(node.Teardown, 'preflight', return_value=[]), \
             patch.object(node.Teardown, 'workloads') as workloads:
            with self.assertRaises(Finished):
                node.main()
            workloads.assert_not_called()
        self.assertFalse(result['changed'])

    def test_failure_report_keeps_earlier_warnings(self):
        module = self.module('workloads')
        result = {}

        def finish(**kwargs):
            result.update(kwargs)
            raise Finished()
        module.fail_json = finish

        def workloads(teardown):
            teardown.warnings.append('containerd CRI cleanup: crictl is required')
            raise ValueError('containerd tasks remain in namespace k8s.io')
        with patch.object(node, 'AnsibleModule', return_value=module), \
             patch.object(node.Teardown, 'workloads', workloads):
            with self.assertRaises(Finished):
                node.main()
        self.assertIn('tasks remain', result['msg'])
        self.assertEqual(module.warned, ['containerd CRI cleanup: crictl is required'])

    def test_leftover_pod_namespace_or_veth_fails_verification(self):
        teardown = node.Teardown(self.module('verify'))
        teardown.remaining = lambda: []
        teardown.paths = []
        teardown.tools = {'ip': None}
        netns = '100 1 0:4 net:[1] /run/netns/cni-93f0705d-9b9a-f601-90be-a102ffe35698 rw - nsfs nsfs rw\n'
        with patch.object(node, 'read_text', return_value=netns):
            with self.assertRaisesRegex(ValueError, 'network namespaces remain'):
                teardown.verify()
        with patch.object(node, 'read_text', return_value=''), \
             patch.object(teardown, 'owned_links', return_value=['lxc5a4a4e3a097a']):
            with self.assertRaisesRegex(ValueError, 'interfaces remain'):
                teardown.verify()

    def test_cleanup_detaches_pod_namespaces_before_links(self):
        teardown = node.Teardown(self.module('cleanup'))
        order = []
        teardown.kill_remaining = lambda: order.append('kill')
        teardown.pod_namespaces = lambda: order.append('netns')
        teardown.networking = lambda: order.append('links')
        teardown.unpin_bpf = lambda: order.append('bpf')
        with patch.object(node, 'cleanup_storage', return_value=False):
            teardown.cleanup()
        self.assertEqual(order, ['kill', 'netns', 'links', 'bpf'])

    def test_engine_apis_run_before_standalone_oci_cleanup(self):
        teardown = node.Teardown(self.module('workloads'))
        order = []
        teardown.preflight = lambda: []
        teardown.engine_cleanup = lambda: order.append('engines')
        teardown.require_tool = lambda name: name
        with patch.object(node.os.path, 'isdir', side_effect=lambda p: p == '/run/crun'), \
             patch.object(node.os, 'listdir', return_value=['x']), \
             patch.object(node, 'stop_oci', side_effect=lambda *a: order.append('oci')), \
             patch.object(node, 'processes', return_value=[]):
            teardown.workloads()
        self.assertEqual(order, ['engines', 'oci'])

    def test_unrelated_ipset_names_do_not_abort_cleanup(self):
        teardown = node.Teardown(self.module('cleanup'))
        teardown.tools = {'ip': None}
        calls = []

        def run(args, mutation=False):
            calls.append(args)
            if args[:2] == ['ipset', 'list']:
                return 'f2b-sshd+\nblocklist/v4\nKUBE-LOAD-BALANCER\n'
            return ''
        teardown.run = run
        with patch.object(node.shutil, 'which', side_effect=lambda name: '/sbin/ipset' if name == 'ipset' else None):
            teardown.networking()
        self.assertIn(['ipset', 'destroy', 'KUBE-LOAD-BALANCER'], calls)
        self.assertFalse(any('f2b-sshd+' in c or 'blocklist/v4' in c for c in calls))

    def test_process_failure_prevents_data_deletion(self):
        teardown = node.Teardown(self.module('cleanup'))
        teardown.kill_remaining = lambda: (_ for _ in ()).throw(ValueError('process remains'))
        with patch.object(node, 'cleanup_storage') as cleanup:
            with self.assertRaisesRegex(ValueError, 'process remains'):
                teardown.cleanup()
            cleanup.assert_not_called()

    def test_veth_peer_already_deleted_is_skipped(self):
        teardown = node.Teardown(self.module('cleanup'))
        teardown.tools = {'ip': 'ip'}
        links = [{'ifname': 'cilium_host'}, {'ifname': 'cilium_net'}, {'ifname': 'eth0'}]

        def run(args, mutation=False):
            import json
            if args == ['ip', '-j', 'link', 'show']:
                return json.dumps(links)
            self.assertEqual(args, ['ip', 'link', 'delete', 'dev', 'cilium_host'])
            links[:] = [{'ifname': 'eth0'}]
            return ''
        teardown.run = run
        with patch.object(node.shutil, 'which', return_value=None):
            teardown.networking()
        self.assertEqual(links, [{'ifname': 'eth0'}])
