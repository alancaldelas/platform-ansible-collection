#!/usr/bin/python
# SPDX-License-Identifier: GPL-2.0-or-later

DOCUMENTATION = r'''
---
module: k8s_uninstall_node
short_description: Perform local destructive Kubernetes node teardown phases
description:
  - Internal implementation of the k8s_uninstall role.
  - Removes all rootful containers, including non-Kubernetes containers.
  - Refuses detected rootless engines and unsafe storage paths.
options:
  phase:
    type: str
    required: true
    description: Teardown phase to execute.
    choices: [preflight, workloads, cleanup, verify]
  confirmation:
    type: str
    default: ''
    description: Must equal REMOVE-ALL-CONTAINERS outside check mode.
  extra_data_paths:
    type: list
    elements: str
    default: []
    description: Additional dedicated data directories to destroy.
  config_files:
    type: list
    elements: str
    default: []
    description: Explicit configuration files validated before removal.
  verify_binaries:
    type: list
    elements: str
    default: []
    description: Executables that must be absent from PATH in the verify phase.
  tracked_processes:
    type: list
    elements: dict
    default: []
    description: Process identities captured before runtime shutdown.
  packages:
    type: list
    elements: str
    default: []
    description: Installed packages selected for removal; preflight reports which can be removed without cascading onto unlisted packages.
  command_timeout:
    type: int
    default: 120
    description: Maximum seconds for each local command.
author:
  - Alan Caldelas
attributes:
  check_mode:
    support: full
'''
EXAMPLES = r'''
- name: Preview local uninstall scope
  alancaldelas.kubernetes_baremetal.k8s_uninstall_node:
    phase: preflight
  check_mode: true
'''
RETURN = r'''
data_paths:
  description: Validated directories included in removal.
  returned: always
  type: list
commands:
  description: Commands executed during this phase.
  returned: always
  type: list
'''

import glob
import json
import os
import pwd
import re
import shutil
import signal
import subprocess
import time

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.alancaldelas.kubernetes_baremetal.plugins.module_utils.uninstall import (
    DATA_PATHS, cleanup_storage, configured_storage, configuration_processes, validate_file_paths, identifiers, iptables_cleanup_commands, mounts_under, owned_interface,
    pinned_bpf_objects, pod_network_namespaces, remove_tree, removable_packages, require_confirmation, validate_data_paths,
    stop_containerd, stop_cri, stop_oci,
)


PROCESS_NAMES = {
    'kubelet', 'kube-proxy', 'kube-apiserver', 'kube-controller-manager',
    'kube-scheduler', 'etcd', 'dockerd', 'containerd', 'crio', 'cri-dockerd',
    'podman', 'conmon', 'runc', 'crun', 'rootlesskit',
}
TOOLS = ['kubeadm', 'crictl', 'ctr', 'docker', 'podman', 'ip', 'umount', 'runc', 'crun', 'rpm']
CONTAINER_CGROUP = re.compile(r'kubepods|/docker/|docker-[0-9a-f]{12,}|libpod-[0-9a-f]{12,}|/cri-containerd-')


def read_text(path):
    with open(path, encoding='utf-8', errors='replace') as stream:
        return stream.read()


def processes():
    all_processes = {}
    selected = set()
    for path in glob.glob('/proc/[0-9]*'):
        try:
            pid = int(path.rsplit('/', 1)[1])
            argv = read_text(path + '/cmdline').split('\x00')
            if not argv[0]:
                continue
            name = os.path.basename(argv[0])
            cgroup = read_text(path + '/cgroup')
            stat = read_text(path + '/stat').rsplit(')', 1)[1].split()
            all_processes[pid] = {'pid': pid, 'name': name, 'uid': os.stat(path).st_uid,
                                  'start': stat[19], 'parent': int(stat[1]), 'argv': argv}
            if name in PROCESS_NAMES or name.startswith('containerd-shim') or CONTAINER_CGROUP.search(cgroup):
                selected.add(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue
    # Standalone containerd tasks can use arbitrary cgroups. Capture descendants
    # before stopping engines, so daemon shutdown cannot hide orphaned payloads.
    while True:
        children = {pid for pid, proc in all_processes.items() if proc['parent'] in selected}
        if children <= selected:
            break
        selected.update(children)
    return [all_processes[pid] for pid in selected]



class Teardown:
    def __init__(self, module):
        self.module = module
        self.commands = []
        self.changed = False
        self.warnings = []
        self.tracked_processes = module.params.get('tracked_processes', [])
        self.paths = validate_data_paths(DATA_PATHS + module.params['extra_data_paths'])
        self.tools = {name: shutil.which(name) for name in TOOLS}
        validate_file_paths(module.params.get('config_files', []))

    def run(self, args, mutation=False):
        self.commands.append(args)
        if mutation:
            if self.module.check_mode:
                raise ValueError('Mutation attempted during check mode')
            self.changed = True
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True,
                                timeout=self.module.params['command_timeout'],
                                env=dict(os.environ, LC_ALL='C'))
        if result.returncode:
            raise RuntimeError('%s failed (%s): %s' % (args[0], result.returncode, result.stderr.strip()))
        return result.stdout

    def runtime_command(self, args):
        # Listing operations and mutation share one adapter in the pure helpers.
        return self.run(args, mutation=not any(word in args for word in ('list', 'ps', 'pods', 'state')))

    def require_tool(self, name):
        if not self.tools.get(name):
            raise ValueError('%s is required to clean up this installed runtime; install the tool and retry' % name)
        return self.tools[name]

    def check_storage(self, path):
        if path and (not os.path.isabs(path) or not any(
                os.path.realpath(path) == os.path.realpath(root) or
                os.path.realpath(path).startswith(os.path.realpath(root) + '/') for root in self.paths)):
            raise ValueError('Custom runtime storage %s must be listed explicitly in k8s_uninstall_extra_data_paths' % path)

    def attempt(self, label, operation):
        try:
            return operation()
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
            self.warnings.append('%s: %s; mandatory offline cleanup and verification will follow' % (label, error))


    def installed_dependents(self, package):
        # Only RPM systems need this: apt cascades removals itself. rpm exits 1
        # with 'no package requires' when nothing depends on the package.
        if not self.tools['rpm']:
            return []
        result = subprocess.run([self.tools['rpm'], '-q', '--whatrequires', '--queryformat', '%{NAME}\n', package],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                                timeout=self.module.params['command_timeout'], env=dict(os.environ, LC_ALL='C'))
        if result.returncode:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith('no package')]

    def package_plan(self):
        return removable_packages(self.module.params.get('packages', []), self.installed_dependents)

    def preflight(self):
        if os.geteuid() != 0:
            raise ValueError('Node uninstall requires become: true (root)')
        if CONTAINER_CGROUP.search(read_text('/proc/self/cgroup')):
            raise ValueError('Refusing to uninstall the host from inside a container')
        if os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv'):
            raise ValueError('Run node uninstall on the host, not in a container')
        current = processes()
        # Container payloads may run as non-root; only rootless engine processes count.
        rootless = [p for p in current if p['uid'] != 0 and
                    (p['name'] in {'podman', 'dockerd', 'containerd', 'conmon', 'rootlesskit'} or
                     p['name'].startswith('containerd-shim'))]
        rootless_storage = [entry.pw_name for entry in pwd.getpwall() if entry.pw_uid != 0 and
                            (os.path.isdir(entry.pw_dir + '/.local/share/containers/storage') or
                             os.path.isdir(entry.pw_dir + '/.local/share/docker'))]
        if rootless or rootless_storage:
            raise ValueError('Rootless container engines detected. Remove them as their owning users first: %s %s' %
                             ([p['pid'] for p in rootless], rootless_storage))
        # Refuse custom storage before any API can remove volumes.
        files = ['/etc/containerd/config.toml', '/etc/crio/crio.conf', '/etc/containers/storage.conf',
                 '/etc/containers/containers.conf']
        files += glob.glob('/etc/crio/crio.conf.d/*.conf')
        files += glob.glob('/etc/containers/containers.conf.d/*.conf')
        docker_configs = ['/etc/docker/daemon.json']
        for process in configuration_processes(current):
            argv = process['argv']
            for index, arg in enumerate(argv):
                flag, sep, value = arg.partition('=')
                if not sep and index + 1 < len(argv):
                    value = argv[index + 1]
                if flag in ('--root-dir', '--data-root', '--root', '--state', '--runroot', '--graphroot'):
                    self.check_storage(value)
                elif flag in ('--config', '-c', '--config-file', '--config-dir') and process['name'] in ('containerd', 'crio', 'dockerd'):
                    self.check_storage(value)
                    if flag == '--config-dir':
                        files += glob.glob(value + '/*.conf')
                    elif process['name'] == 'dockerd':
                        docker_configs.append(value)
                    else:
                        files.append(value)
        for filename in files:
            for root in configured_storage(filename):
                self.check_storage(root)
        for filename in docker_configs:
            if os.path.isfile(filename):
                self.check_storage(json.loads(read_text(filename)).get('data-root'))
        if os.path.exists('/run/docker.sock') and self.tools['docker']:
            root = self.attempt('Docker storage inspection', lambda: self.run(
                [self.tools['docker'], '--host', 'unix:///run/docker.sock', 'info', '--format', '{{.DockerRootDir}}']).strip())
            self.check_storage(root)
        # podman info can initialize storage, so never run it in check mode.
        if not self.module.check_mode and self.tools['podman'] and os.path.exists('/var/lib/containers/storage'):
            raw = self.attempt('Podman storage inspection', lambda: self.run(
                [self.tools['podman'], '--remote=false', 'info', '--format', 'json']))
            if raw:
                info = json.loads(raw)
                for key in ('graphRoot', 'runRoot', 'volumePath'):
                    self.check_storage(info.get('store', {}).get(key))
        for runtime in ('runc', 'crun'):
            root = '/run/' + runtime
            if os.path.isdir(root) and os.listdir(root):
                self.run([self.require_tool(runtime), '--root', root, 'list', '-q'])
        self.require_tool('umount')
        return current

    def workloads(self):
        self.tracked_processes = self.preflight()
        self.engine_cleanup()
        for runtime in ('runc', 'crun'):
            root = '/run/' + runtime
            if os.path.isdir(root) and os.listdir(root):
                # Engine-managed containers are gone by now; whatever is left is
                # standalone and has no daemon fallback, so removal must be proven.
                stop_oci(self.runtime_command, self.require_tool(runtime), root)
        self.tracked_processes += processes()

    def engine_cleanup(self):
        if os.path.exists('/run/docker.sock'):
            def docker_cleanup():
                base = [self.require_tool('docker'), '--host', 'unix:///run/docker.sock']
                for container in identifiers(self.run(base + ['ps', '-aq'])):
                    self.run(base + ['rm', '--force', '--volumes', container], mutation=True)
            self.attempt('Docker cleanup', docker_cleanup)
        if self.tools['podman'] and os.path.exists('/var/lib/containers/storage'):
            self.attempt('Podman cleanup', lambda: self.run(
                [self.tools['podman'], '--remote=false', 'rm', '--all', '--force', '--volumes'], mutation=True))
        if os.path.exists('/run/crio/crio.sock'):
            self.attempt('CRI-O cleanup', lambda: stop_cri(
                self.runtime_command, self.require_tool('crictl'), 'unix:///run/crio/crio.sock'))
        if os.path.exists('/run/containerd/containerd.sock'):
            if self.tools['crictl']:
                self.attempt('containerd CRI cleanup', lambda: stop_cri(
                    self.runtime_command, self.tools['crictl'], 'unix:///run/containerd/containerd.sock'))
            self.attempt('containerd task cleanup', lambda: stop_containerd(
                self.runtime_command, self.require_tool('ctr'), '/run/containerd/containerd.sock'))

    def remaining(self):
        found = {proc['pid']: proc for proc in processes()}
        for proc in self.tracked_processes:
            try:
                stat = read_text('/proc/%s/stat' % proc['pid']).rsplit(')', 1)[1].split()
                if stat[19] == proc['start'] and stat[0] != 'Z':
                    found[proc['pid']] = proc
            except (FileNotFoundError, ProcessLookupError):
                pass
        return list(found.values())

    def kill_remaining(self):
        for process in self.remaining():
            pid = process['pid']
            if pid in (1, os.getpid(), os.getppid()):
                raise ValueError('Refusing to kill the uninstall process or PID 1')
            try:
                start = read_text('/proc/%s/stat' % pid).rsplit(')', 1)[1].split()[19]
                if start == process['start']:
                    os.kill(pid, signal.SIGKILL)
                    self.changed = True
            except (FileNotFoundError, ProcessLookupError):
                pass
        for attempt in range(20):
            remaining = self.remaining()
            if not remaining:
                return
            time.sleep(0.25)
        raise ValueError('Runtime/container processes still running: %s' % [p['pid'] for p in remaining])

    def pod_namespaces(self):
        # Detach pod network namespaces first: destroying one removes its veth pair.
        for path in pod_network_namespaces(read_text('/proc/self/mountinfo')):
            self.run([self.require_tool('umount'), '--', path], mutation=True)
            if os.path.lexists(path):
                os.unlink(path)

    def owned_links(self):
        if not self.tools['ip']:
            return []
        return [link['ifname'] for link in json.loads(self.run([self.tools['ip'], '-j', 'link', 'show']))
                if owned_interface(link['ifname'])]

    def unpin_bpf(self):
        for path in pinned_bpf_objects():
            self.changed = remove_tree(path, read_text('/proc/self/mountinfo')) or self.changed

    def networking(self):
        for save, executable in [('iptables-save', 'iptables'), ('ip6tables-save', 'ip6tables')]:
            if shutil.which(save) and shutil.which(executable):
                for args in iptables_cleanup_commands(self.run([save]), executable):
                    self.run(args, mutation=True)
        if shutil.which('nft'):
            tables = json.loads(self.run(['nft', '-j', 'list', 'tables'])).get('nftables', [])
            for entry in tables:
                table = entry.get('table', {})
                if table.get('name') in ('kube-proxy', 'cilium', 'netavark', 'docker-bridges'):
                    self.run(['nft', 'delete', 'table', table['family'], table['name']], mutation=True)
        if shutil.which('ipset'):
            # Only names that will be passed to destroy are validated; unrelated
            # administrator sets may use characters identifiers() rejects.
            owned = [name for name in self.run(['ipset', 'list', '-name']).split()
                     if name.startswith(('KUBE-', 'cali', 'CILIUM_', 'weave'))]
            for name in identifiers(' '.join(owned)):
                self.run(['ipset', 'destroy', name], mutation=True)
        for name in self.owned_links():
            # Deleting one side of a veth also removes its peer.
            if name in self.owned_links():
                self.run([self.tools['ip'], 'link', 'delete', 'dev', name], mutation=True)

    def cleanup(self):
        self.kill_remaining()
        self.pod_namespaces()
        self.networking()
        self.unpin_bpf()
        # Never lazy-unmount: an attached remote volume must not be traversed.
        self.changed = cleanup_storage(
            self.paths, lambda: read_text('/proc/self/mountinfo'),
            lambda path: self.run([self.require_tool('umount'), '--', path], mutation=True)
        ) or self.changed

    def verify(self):
        remaining = self.remaining()
        if remaining:
            raise ValueError('Runtime/container processes remain: %s' % [p['pid'] for p in remaining])
        executables = [name for name in self.module.params.get('verify_binaries', []) if shutil.which(name)]
        if executables:
            raise ValueError('Executables remain on PATH; remove their custom installation and retry: %s' % executables)
        leftovers = [p for p in self.paths if os.path.lexists(p)]
        if leftovers:
            raise ValueError('Uninstall data directories remain: %s' % leftovers)
        namespaces = pod_network_namespaces(read_text('/proc/self/mountinfo'))
        if namespaces:
            raise ValueError('Pod network namespaces remain mounted: %s' % namespaces)
        links = self.owned_links()
        if links:
            raise ValueError('Container network interfaces remain: %s' % links)
        pinned = pinned_bpf_objects()
        if pinned:
            raise ValueError('Pinned CNI BPF objects remain: %s' % pinned)


def report_warnings(module, teardown):
    for warning in (teardown.warnings if teardown else []):
        module.warn(warning)


def main():
    module = AnsibleModule(argument_spec={
        'phase': {'type': 'str', 'required': True, 'choices': ['preflight', 'workloads', 'cleanup', 'verify']},
        'confirmation': {'type': 'str', 'default': ''},
        'extra_data_paths': {'type': 'list', 'elements': 'str', 'default': []},
        'command_timeout': {'type': 'int', 'default': 120},
        'config_files': {'type': 'list', 'elements': 'str', 'default': []},
        'verify_binaries': {'type': 'list', 'elements': 'str', 'default': []},
        'tracked_processes': {'type': 'list', 'elements': 'dict', 'default': []},
        'packages': {'type': 'list', 'elements': 'str', 'default': []},
    }, supports_check_mode=True)
    teardown = None
    try:
        require_confirmation(module.params['confirmation'], module.check_mode)
        teardown = Teardown(module)
        if module.check_mode or module.params['phase'] == 'preflight':
            observed = teardown.preflight()
            removable, retained = teardown.package_plan()
            for package, blockers in sorted(retained.items()):
                teardown.warnings.append('Keeping package %s: still required by %s' % (package, ', '.join(blockers)))
            report_warnings(module, teardown)
            module.exit_json(changed=False, data_paths=teardown.paths,
                             commands=teardown.commands, processes=observed,
                             tools=teardown.tools, removable_packages=removable, retained_packages=retained,
                             existing_data_paths=[p for p in teardown.paths if os.path.lexists(p)])
        getattr(teardown, module.params['phase'])()
        report_warnings(module, teardown)
        module.exit_json(changed=teardown.changed, data_paths=teardown.paths, commands=teardown.commands,
                         tracked_processes=teardown.tracked_processes)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        # Warnings explain why an API cleanup was skipped; keep them on failure too.
        report_warnings(module, teardown)
        module.fail_json(msg=str(error), changed=teardown.changed if teardown else False,
                         commands=teardown.commands if teardown else [])


if __name__ == '__main__':
    main()
