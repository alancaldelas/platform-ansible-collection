import importlib.util
import pathlib
import tempfile
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[2] / 'plugins/module_utils/uninstall.py'


def load_helper():
    spec = importlib.util.spec_from_file_location('uninstall', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UninstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE.exists():
            cls.helper = load_helper()

    def setUp(self):
        self.assertTrue(SOURCE.exists(), 'The tested uninstall helper is not implemented')

    def test_confirmation_required_for_mutation(self):
        with self.assertRaises(ValueError):
            self.helper.require_confirmation('', False)
        self.helper.require_confirmation('REMOVE-ALL-CONTAINERS', False)

    def test_check_mode_needs_no_confirmation(self):
        self.helper.require_confirmation('', True)

    def test_rejects_broad_or_relative_deletion_paths(self):
        for path in ['/', '/var', '/var/lib', '/etc', '/usr/local', '/home/alice',
                     '/root', '/srv', '', 'var/lib/containerd', '/srv/../etc']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.helper.validate_data_paths([path])

    def test_allows_dedicated_custom_storage(self):
        self.assertEqual(self.helper.validate_data_paths(['/srv/container-data']), ['/srv/container-data'])

    def test_mount_order_is_deepest_first_and_boundary_aware(self):
        data = '\n'.join([
            '1 0 0:1 / /var/lib/kubelet rw - ext4 /dev/a rw',
            '2 1 0:2 / /var/lib/kubelet/pods/a rw - tmpfs tmpfs rw',
            '3 2 0:3 / /var/lib/kubelet/pods/a/volumes/data\\040disk rw - nfs server:/data rw',
            '4 0 0:4 / /var/lib/kubelet-other rw - ext4 /dev/b rw',
        ])
        self.assertEqual(self.helper.mounts_under(['/var/lib/kubelet'], data), [
            '/var/lib/kubelet/pods/a/volumes/data disk', '/var/lib/kubelet/pods/a', '/var/lib/kubelet'])

    def test_removal_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            outside = base / 'outside'
            outside.mkdir()
            (outside / 'keep').write_text('valuable')
            data = base / 'data'
            data.mkdir()
            (data / 'link').symlink_to(outside, target_is_directory=True)
            self.helper.remove_tree(str(data), '')
            self.assertFalse(data.exists())
            self.assertEqual((outside / 'keep').read_text(), 'valuable')

    def test_refuses_removal_while_any_child_is_mounted(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp) / 'data'
            data.mkdir()
            (data / 'keep').write_text('still mounted')
            mounts = f'1 0 0:1 / {data}/volume rw - nfs server:/data rw'
            with self.assertRaises(ValueError):
                self.helper.remove_tree(str(data), mounts)
            self.assertTrue((data / 'keep').exists())

    def test_refuses_symlink_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            (base / 'actual').mkdir()
            (base / 'link').symlink_to(base / 'actual', target_is_directory=True)
            with self.assertRaises(ValueError):
                self.helper.remove_tree(str(base / 'link' / 'child'), '')

    def test_missing_tree_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(self.helper.remove_tree(tmp + '/missing', ''))

    def test_containerd_cleans_every_namespace_and_checks_no_tasks_remain(self):
        calls = []
        tasks = {'k8s.io': ['pod-task'], 'default': ['standalone']}

        def run(args):
            calls.append(args)
            if args[-3:] == ['namespaces', 'list', '-q']:
                return 'k8s.io\ndefault\n'
            ns = args[args.index('--namespace') + 1]
            if args[-3:] == ['tasks', 'list', '-q']:
                return '\n'.join(tasks[ns])
            if 'delete' in args:
                tasks[ns].remove(args[-1])
            return ''

        self.helper.stop_containerd(run, '/usr/local/bin/ctr', '/run/containerd/containerd.sock')
        self.assertEqual(tasks, {'k8s.io': [], 'default': []})
        kills = [c for c in calls if 'kill' in c]
        self.assertEqual(len(kills), 2)
        self.assertTrue(all('--all' in c and 'SIGKILL' in c for c in kills))

    def test_cri_removes_containers_before_sandboxes(self):
        calls = []
        containers, pods = ['container-id'], ['sandbox-id']

        def run(args):
            calls.append(args)
            if args[-3:] == ['ps', '-a', '-q']:
                return '\n'.join(containers)
            if args[-2:] == ['pods', '-q']:
                return '\n'.join(pods)
            if 'rm' in args:
                containers.clear()
            if 'rmp' in args:
                self.assertEqual(containers, [])
                pods.clear()
            return ''

        self.helper.stop_cri(run, '/usr/bin/crictl', 'unix:///run/crio/crio.sock')
        self.assertEqual(containers + pods, [])
        self.assertTrue(any('stopp' in c for c in calls))

    def test_command_failure_propagates(self):
        def run(args):
            raise RuntimeError('runtime API unavailable')
        with self.assertRaisesRegex(RuntimeError, 'unavailable'):
            self.helper.stop_containerd(run, 'ctr', '/run/containerd/containerd.sock')

    def test_stopped_containerd_task_is_still_removed(self):
        tasks = ['stopped-task']

        def run(args):
            if args[-3:] == ['namespaces', 'list', '-q']:
                return 'default'
            if args[-3:] == ['tasks', 'list', '-q']:
                return '\n'.join(tasks)
            if 'kill' in args:
                raise RuntimeError('process already exited')
            if 'delete' in args:
                tasks.clear()
            return ''
        self.helper.stop_containerd(run, 'ctr', '/run/containerd/containerd.sock')
        self.assertEqual(tasks, [])

    def test_dedicated_mounted_data_is_erased_before_unmount(self):
        self.assertTrue(hasattr(self.helper, 'cleanup_storage'), 'Mounted storage cleanup missing')
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp) / 'runtime'
            data.mkdir()
            (data / 'image').write_text('destroy this')
            mounts = [f'1 0 0:1 / {data} rw - ext4 /dev/a rw']

            def unmount(path):
                self.assertEqual(path, str(data))
                self.assertEqual(list(data.iterdir()), [])
                mounts.clear()

            self.helper.cleanup_storage([str(data)], lambda: '\n'.join(mounts), unmount)
            self.assertFalse(data.exists())

    def test_host_firewall_chains_are_preserved(self):
        rules = '*filter\n:INPUT ACCEPT [0:0]\n:SSH-GUARD - [0:0]\n:KUBE-FORWARD - [0:0]\n-A INPUT -j SSH-GUARD\n-A FORWARD -j KUBE-FORWARD\n-A KUBE-FORWARD -j ACCEPT\nCOMMIT\n'
        commands = self.helper.iptables_cleanup_commands(rules, 'iptables')
        self.assertIn(['iptables', '-w', '-t', 'filter', '-D', 'FORWARD', '-j', 'KUBE-FORWARD'], commands)
        self.assertIn(['iptables', '-w', '-t', 'filter', '-X', 'KUBE-FORWARD'], commands)
        self.assertFalse(any('SSH-GUARD' in c or c[-1] == 'INPUT' for c in commands))

    def test_docker_user_firewall_chain_is_preserved(self):
        rules = '*filter\n:DOCKER-USER - [0:0]\n:DOCKER-FORWARD - [0:0]\n-A FORWARD -j DOCKER-USER\nCOMMIT\n'
        commands = self.helper.iptables_cleanup_commands(rules, 'iptables')
        self.assertFalse(any('DOCKER-USER' in c for c in commands))

    def test_storage_roots_include_imported_snapshotter_config(self):
        self.assertTrue(hasattr(self.helper, 'configured_storage'), 'Effective configuration discovery missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'main.toml').write_text('root="/var/lib/containerd"\nimports=["drop-in.toml"]\n')
            (root / 'drop-in.toml').write_text('[plugins.snapshotter]\nroot_path="/srv/custom-snapshots"\n')
            self.assertEqual(set(self.helper.configured_storage(str(root / 'main.toml'))),
                             {'/var/lib/containerd', '/srv/custom-snapshots'})

    def test_unrelated_network_interfaces_are_not_selected(self):
        self.assertTrue(self.helper.owned_interface('cilium_host'))
        self.assertTrue(self.helper.owned_interface('cali01234'))
        self.assertTrue(self.helper.owned_interface('flannel.1'))
        self.assertFalse(self.helper.owned_interface('eth0'))
        self.assertFalse(self.helper.owned_interface('br0'))

    def test_configuration_file_cannot_be_a_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'is a directory'):
                self.helper.validate_file_paths([tmp])

    def test_conmon_wrapped_podman_storage_arguments_are_decoded(self):
        process = {'name': 'conmon', 'argv': [
            '/usr/bin/conmon', '--exit-command', '/usr/bin/podman',
            '--exit-command-arg', '--root', '--exit-command-arg', '/srv/podman-data',
            '--exit-command-arg=--runroot', '--exit-command-arg=/run/containers/storage',
            '--exit-command-arg', 'container', '--exit-command-arg', 'cleanup',
        ]}
        parsed = list(self.helper.configuration_processes([process]))
        self.assertEqual(parsed, [{'name': 'podman', 'argv': [
            '/usr/bin/podman', '--root', '/srv/podman-data', '--runroot',
            '/run/containers/storage', 'container', 'cleanup']}])

    def test_detached_oci_containers_are_killed_before_state_removal(self):
        calls = []
        containers = ['detached']

        def run(args):
            calls.append(args)
            if args[-2:] == ['list', '-q']:
                return '\n'.join(containers)
            if 'state' in args:
                return '{"status":"running"}'
            if 'delete' in args:
                self.assertTrue(any(cmd[-4:] == ['kill', '--all', 'detached', 'KILL'] for cmd in calls))
                containers.clear()
            return ''
        self.helper.stop_oci(run, 'crun', '/run/crun')
        self.assertIn(['crun', '--root', '/run/crun', 'kill', '--all', 'detached', 'KILL'], calls)
        self.assertEqual(containers, [])

    def test_storage_roots_are_found_without_a_toml_parser(self):
        import sys
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'main.toml').write_text(
                'version = 2\nroot = "/var/lib/containerd"  # data\n'
                "state = '/run/containerd'\nimports = [\n  \"drop-in.toml\",\n]\n"
                '[plugins."io.containerd.grpc.v1.cri"]\n  root_path_unrelated = "/nope"\n')
            (root / 'drop-in.toml').write_text('[plugins.snapshotter]\nroot_path="/srv/custom-snapshots"\n')
            with patch.dict(sys.modules, {'tomllib': None, 'tomli': None}):
                found = set(self.helper.configured_storage(str(root / 'main.toml')))
        self.assertEqual(found, {'/var/lib/containerd', '/run/containerd', '/srv/custom-snapshots'})

    def test_pod_network_namespaces_are_selected_by_name(self):
        mountinfo = (
            '100 1 0:4 net:[1] /run/netns/cni-93f0705d-9b9a-f601-90be-a102ffe35698 rw - nsfs nsfs rw\n'
            '101 1 0:4 net:[2] /var/run/netns/netns-6b0a3b5c-1111-2222-3333-444444444444 rw - nsfs nsfs rw\n'
            '102 1 0:4 net:[3] /run/netns/7f3d2b6a-1111-2222-3333-444444444444 rw - nsfs nsfs rw\n'
            '103 1 0:4 net:[4] /run/netns/admin-lab rw - nsfs nsfs rw\n'
            '104 1 0:4 net:[5] /srv/netns/cni-93f0705d-9b9a-f601-90be-a102ffe35698 rw - nsfs nsfs rw\n'
        )
        self.assertEqual(self.helper.pod_network_namespaces(mountinfo), [
            '/run/netns/7f3d2b6a-1111-2222-3333-444444444444',
            '/run/netns/cni-93f0705d-9b9a-f601-90be-a102ffe35698',
            '/var/run/netns/netns-6b0a3b5c-1111-2222-3333-444444444444',
        ])

    def test_cilium_endpoint_veths_are_owned_but_lxc_bridges_are_not(self):
        self.assertTrue(self.helper.owned_interface('lxc5a4a4e3a097a'))
        self.assertTrue(self.helper.owned_interface('lxc_health'))
        self.assertTrue(self.helper.owned_interface('podman0'))
        self.assertFalse(self.helper.owned_interface('lxcbr0'))
        self.assertFalse(self.helper.owned_interface('lxc-container0'))

    def test_pinned_bpf_objects_include_cilium_tree_and_tc_globals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'cilium' / 'devices').mkdir(parents=True)
            (root / 'tc' / 'globals').mkdir(parents=True)
            (root / 'tc' / 'globals' / 'cilium_calls_00890').touch()
            (root / 'tc' / 'globals' / 'other_map').touch()
            self.assertEqual(self.helper.pinned_bpf_objects(tmp),
                             [tmp + '/cilium', tmp + '/tc/globals/cilium_calls_00890'])

    def test_oci_container_reaped_between_kill_and_delete_is_tolerated(self):
        containers = ['managed']

        def run(args):
            if args[-2:] == ['list', '-q']:
                return '\n'.join(containers)
            if 'state' in args:
                return '{"status":"running"}'
            if 'kill' in args:
                containers.clear()  # conmon's exit command removed the state
                return ''
            if 'delete' in args:
                raise RuntimeError('crun failed (1): container `managed` does not exist')
            return ''
        self.helper.stop_oci(run, 'crun', '/run/crun')

    def test_containerd_task_reaped_between_kill_and_delete_is_tolerated(self):
        tasks = ['abc123']

        def run(args):
            if args[-3:] == ['namespaces', 'list', '-q']:
                return 'k8s.io'
            if args[-3:] == ['tasks', 'list', '-q']:
                return '\n'.join(tasks)
            if 'kill' in args:
                tasks.clear()
                return ''
            if 'delete' in args:
                raise RuntimeError('ctr failed (1): task abc123 not found')
            return ''
        self.helper.stop_containerd(run, 'ctr', '/run/containerd/containerd.sock')

    def test_oci_container_that_survives_delete_still_fails(self):
        def run(args):
            if args[-2:] == ['list', '-q']:
                return 'stuck'
            if 'state' in args:
                return '{"status":"running"}'
            if 'delete' in args:
                raise RuntimeError('crun failed (1): busy')
            return ''
        with self.assertRaisesRegex(ValueError, 'containers remain'):
            self.helper.stop_oci(run, 'crun', '/run/crun')

    def test_packages_needed_by_unlisted_software_are_retained(self):
        graph = {
            'containers-common': ['containers-common-extra', 'skopeo'],
            'containers-common-extra': ['buildah', 'podman'],
            'netavark': ['containers-common-extra'],
            'crun': ['containers-common-extra'],
            'conmon': ['podman'],
        }
        candidates = ['podman', 'buildah', 'containers-common', 'containers-common-extra', 'crun', 'netavark', 'conmon', 'kubelet']
        removable, retained = self.helper.removable_packages(candidates, lambda name: graph.get(name, []))
        self.assertEqual(retained, {'containers-common': ['skopeo']})
        self.assertEqual(removable, [p for p in candidates if p != 'containers-common'])

    def test_retention_propagates_to_dependencies_of_kept_packages(self):
        # keeping B (needed by unlisted X) must also keep A, which B needs.
        graph = {'A': ['B'], 'B': ['X']}
        removable, retained = self.helper.removable_packages(['A', 'B', 'C'], lambda name: graph.get(name, []))
        self.assertEqual(removable, ['C'])
        self.assertEqual(retained, {'A': ['B'], 'B': ['X']})

    def test_cyclic_config_imports_terminate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'a.toml').write_text('root="/var/lib/containerd"\nimports=["b.toml"]\n')
            (root / 'b.toml').write_text('state="/run/containerd"\nimports=["a.toml"]\n')
            self.assertEqual(set(self.helper.configured_storage(str(root / 'a.toml'))),
                             {'/var/lib/containerd', '/run/containerd'})


if __name__ == '__main__':
    unittest.main()
