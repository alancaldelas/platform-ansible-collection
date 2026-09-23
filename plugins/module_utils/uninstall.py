# SPDX-License-Identifier: GPL-2.0-or-later
"""Small, shell-free operations used by the destructive node uninstall module."""

import os
import glob
import json
import re
import shlex
import shutil


CONFIRMATION = 'REMOVE-ALL-CONTAINERS'
DATA_PATHS = [
    '/etc/kubernetes', '/var/lib/kubelet', '/var/lib/etcd',
    '/etc/cni/net.d', '/opt/cni/bin', '/var/lib/cni',
    '/etc/containerd', '/var/lib/containerd', '/run/containerd',
    '/etc/docker', '/var/lib/docker', '/run/docker',
    '/etc/crio', '/run/crio', '/var/lib/crio',
    '/etc/containers', '/var/lib/containers', '/run/containers', '/run/libpod',
    '/var/lib/calico', '/run/calico', '/var/lib/cilium', '/run/cilium',
    '/run/flannel', '/var/lib/weave', '/var/log/pods', '/var/log/containers',
    '/opt/kubernetes', '/opt/containerd',
    '/run/runc', '/run/crun',
]
CHAIN_PREFIXES = ('KUBE-', 'CILIUM_', 'cali-', 'FLANNEL-', 'WEAVE',
                  'CNI-', 'NETAVARK-', 'DOCKER')


def configuration_processes(processes):
    """Expose real engine options, including Podman's command wrapped by conmon."""
    engines = {'containerd', 'crio', 'dockerd', 'podman', 'kubelet', 'runc', 'crun'}
    for process in processes:
        if process['name'] in engines:
            yield process
        elif process['name'] == 'conmon':
            command, arguments = None, []
            argv = iter(process['argv'][1:])
            for arg in argv:
                flag, sep, value = arg.partition('=')
                if flag in ('--exit-command', '--exit-command-arg'):
                    if not sep:
                        value = next(argv, '')
                    if flag == '--exit-command':
                        command = value
                    else:
                        arguments.append(value)
            if command and os.path.basename(command) == 'podman':
                yield {'name': 'podman', 'argv': [command] + arguments}


STORAGE_KEYS = ('root', 'state', 'root_path', 'runroot', 'graphroot',
                'imagestore', 'static_dir', 'tmp_dir', 'volume_path')


def parse_storage(data):
    """Return (roots, imports) from TOML text.

    A TOML parser is used when available. Nodes without tomllib (Python < 3.11)
    or tomli fall back to a line scan of quoted string values for the known
    storage keys and the top-level imports list, so preflight keeps working on
    RHEL 9 and Ubuntu 22.04 family nodes.
    """
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            tomllib = None
    if tomllib is not None:
        config = tomllib.loads(data)
        roots = []

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in STORAGE_KEYS and isinstance(item, str) and item:
                        roots.append(item)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(config)
        return roots, list(config.get('imports', []))
    keys = '|'.join(STORAGE_KEYS)
    roots = [value for _, value in re.findall(
        r'^\s*(?:%s)\s*=\s*(["\'])([^"\'\n]+)\1' % keys, data, re.MULTILINE)]
    imports = []
    match = re.search(r'^\s*imports\s*=\s*\[(.*?)\]', data, re.MULTILINE | re.DOTALL)
    if match:
        imports = re.findall(r'["\']([^"\'\n]+)["\']', match.group(1))
    return roots, imports


def configured_storage(filename, visited=None):
    """Read TOML storage roots, including containerd imports and plugin roots."""
    if not os.path.isfile(filename):
        return []
    visited = set() if visited is None else visited
    filename = os.path.realpath(filename)
    if filename in visited:
        return []
    visited.add(filename)
    with open(filename, encoding='utf-8') as stream:
        roots, imports = parse_storage(stream.read())
    for pattern in imports:
        if not os.path.isabs(pattern):
            pattern = os.path.join(os.path.dirname(filename), pattern)
        for imported in glob.glob(pattern):
            roots.extend(configured_storage(imported, visited))
    return roots


def validate_file_paths(paths):
    for path in paths:
        if not isinstance(path, str) or not path.startswith('/') or os.path.normpath(path) != path:
            raise ValueError('Expected an absolute configuration file path: %r' % path)
        reject_symlink_ancestors(path)
        if os.path.isdir(path) and not os.path.islink(path):
            raise ValueError('Configuration file path is a directory: %s' % path)
    return paths


def require_confirmation(value, check_mode):
    if not check_mode and value != CONFIRMATION:
        raise ValueError('Set k8s_uninstall_confirmation=REMOVE-ALL-CONTAINERS to destroy all containers and local runtime data')


def validate_data_paths(paths):
    """Accept dedicated directories, never a system/home/storage parent."""
    protected = {'/', '/etc', '/var', '/var/lib', '/var/log', '/run', '/usr',
                 '/usr/local', '/usr/local/bin', '/usr/local/sbin', '/opt',
                 '/srv', '/mnt', '/media', '/tmp', '/home', '/root', '/boot',
                 '/dev', '/proc', '/sys', '/bin', '/sbin', '/lib', '/lib64'}
    result = []
    for path in paths:
        if (not isinstance(path, str) or not path.startswith('/') or
                os.path.normpath(path) != path or '\x00' in path or
                path in protected or path.startswith(('/home/', '/root/', '/usr/',
                                                       '/proc/', '/sys/', '/dev/', '/boot/'))):
            raise ValueError('Refusing unsafe uninstall directory: %r' % path)
        reject_symlink_ancestors(path)
        if os.path.islink(path):
            raise ValueError('Uninstall data root must not be a symlink: %s' % path)
        if path not in result:
            result.append(path)
    return result


def reject_symlink_ancestors(path):
    parent = os.path.dirname(path)
    while parent and parent != '/':
        if os.path.islink(parent) and parent != '/var/run':
            raise ValueError('Refusing path with symlink ancestor: %s' % path)
        parent = os.path.dirname(parent)


def mount_points(mountinfo):
    for line in mountinfo.splitlines():
        fields = line.split()
        if len(fields) >= 6:
            yield re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), fields[4])


def mounts_under(paths, mountinfo):
    mounts = set()
    roots = [os.path.realpath(p) for p in paths]
    for path in mount_points(mountinfo):
        if any(path == root or path.startswith(root + '/') for root in roots):
            mounts.add(path)
    return sorted(mounts, key=lambda p: (p.count('/'), len(p)), reverse=True)


UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
POD_NETNS = re.compile(r'(cni-|netns-)?%s' % UUID)


def pod_network_namespaces(mountinfo):
    """Mounted pod/container network namespaces left by CNI, CRI-O and Podman.

    They live outside every data root, so an offline teardown must detach them
    explicitly or their host-side veth peers survive. Administrator namespaces
    with other names are left alone.
    """
    found = set()
    for path in mount_points(mountinfo):
        parent, name = os.path.split(path)
        if parent in ('/run/netns', '/var/run/netns') and POD_NETNS.fullmatch(name):
            found.add(path)
    return sorted(found)


def pinned_bpf_objects(root='/sys/fs/bpf'):
    """Cilium's pinned maps and links; unpinning the links detaches its programs."""
    found = []
    if os.path.isdir(root + '/cilium'):
        found.append(root + '/cilium')
    found.extend(sorted(glob.glob(root + '/tc/globals/cilium_*')))
    return found


def remove_tree(path, mountinfo):
    reject_symlink_ancestors(path)
    if mounts_under([path], mountinfo):
        raise ValueError('Refusing to delete mounted storage: %s' % path)
    if not os.path.lexists(path):
        return False
    if os.path.islink(path) or not os.path.isdir(path):
        os.unlink(path)
    else:
        # CPython uses fd-relative deletion on Linux, avoiding symlink traversal.
        if not shutil.rmtree.avoids_symlink_attacks:
            raise ValueError('This Python platform lacks symlink-safe rmtree')
        shutil.rmtree(path)
    return True


def cleanup_storage(paths, mountinfo_reader, unmount):
    """Detach child volumes, wipe dedicated mounted roots, then remove roots.

    Child mounts may be remote PVs: detach them without erasing their contents.
    A mount at an explicitly selected data root is dedicated runtime storage:
    erase its contents before detaching it, or removal would only hide the data.
    """
    changed = False
    roots = {os.path.realpath(path) for path in paths}
    for mount in mounts_under(paths, mountinfo_reader()):
        if mount in roots:
            reject_symlink_ancestors(mount)
            for entry in os.scandir(mount):
                changed = remove_tree(entry.path, mountinfo_reader()) or changed
        unmount(mount)
        changed = True
    for path in paths:
        changed = remove_tree(path, mountinfo_reader()) or changed
    return changed


def removable_packages(candidates, dependents_of):
    """Split candidates into (removable, retained) by installed reverse dependencies.

    dnf5 through Ansible refuses to cascade a removal onto packages outside the
    request, so a listed package that another installed package still needs
    (skopeo needing containers-common, for example) is kept rather than
    failing the run. Iterates to a fixed point because retaining one package
    can in turn protect the packages it depends on.
    """
    removable = list(candidates)
    retained = {}
    changed = True
    while changed:
        changed = False
        for package in list(removable):
            blockers = sorted(dep for dep in dependents_of(package) if dep not in removable)
            if blockers:
                removable.remove(package)
                retained[package] = blockers
                changed = True
    return removable, retained


def identifiers(output):
    values = output.split()
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', value) for value in values):
        raise ValueError('Invalid identifier returned by container runtime')
    return values


def stop_containerd(run, ctr, socket):
    base = [ctr, '--address', socket, '--timeout', '30s']
    for namespace in identifiers(run(base + ['namespaces', 'list', '-q'])):
        command = base + ['--namespace', namespace]
        for task in identifiers(run(command + ['tasks', 'list', '-q'])):
            # delete --force kills a task as well; explicit SIGKILL includes execs.
            try:
                run(command + ['tasks', 'kill', '--signal', 'SIGKILL', '--all', task])
            except RuntimeError:
                # Already-exited tasks cannot be signalled.
                pass
            # The shim may reap a killed task before the delete lands. Tolerate
            # that race; the listing below is what proves removal.
            try:
                run(command + ['tasks', 'delete', '--force', task])
            except RuntimeError:
                pass
        if run(command + ['tasks', 'list', '-q']).strip():
            raise ValueError('containerd tasks remain in namespace %s' % namespace)


def stop_cri(run, crictl, endpoint):
    base = [crictl, '--runtime-endpoint', endpoint, '--timeout', '30s']
    for container in identifiers(run(base + ['ps', '-a', '-q'])):
        run(base + ['rm', '--force', container])
    for sandbox in identifiers(run(base + ['pods', '-q'])):
        run(base + ['stopp', sandbox])
        run(base + ['rmp', '--force', sandbox])
    if run(base + ['ps', '-a', '-q']).strip() or run(base + ['pods', '-q']).strip():
        raise ValueError('CRI containers or sandboxes remain at %s' % endpoint)


def stop_oci(run, executable, root):
    """Remove OCI containers left in a runtime state root after engine cleanup.

    /run/runc and /run/crun are also CRI-O's and Podman's runtime roots, so the
    engines' own APIs run first and only leftovers reach this function. A
    container's exit handler (conmon, a shim) may delete its state between the
    kill and the forced delete; that race is tolerated and the final listing
    is what proves removal.
    """
    base = [executable, '--root', root]
    for container in identifiers(run(base + ['list', '-q'])):
        try:
            state = json.loads(run(base + ['state', container]))
        except RuntimeError:
            continue
        if state['status'] != 'stopped':
            try:
                run(base + ['kill', '--all', container, 'KILL'])
            except RuntimeError:
                pass
        try:
            run(base + ['delete', '--force', container])
        except RuntimeError:
            pass
    if run(base + ['list', '-q']).strip():
        raise ValueError('Standalone OCI containers remain at %s' % root)


def owned_interface(name):
    return (name in {'cni0', 'docker0', 'podman0', 'weave', 'datapath', 'vxlan-6784',
                     'tunl0', 'vxlan.calico', 'vxlan-v6.calico', 'wireguard.cali',
                     'wg-v6.cali', 'kube-ipvs0', 'nodelocaldns', 'flannel-v6.1', 'flannel-wg',
                     'lxc_health'} or
            name.startswith(('cilium_', 'cali', 'flannel.', 'vethwe', 'cni-podman')) or
            # Cilium endpoint veths are lxc + 12 hex digits; lxcbr0 and friends are not ours.
            bool(re.fullmatch(r'br-[0-9a-f]{12}|lxc[0-9a-f]{12}', name)))


def iptables_cleanup_commands(saved, executable):
    """Detach references, flush owned chains, then delete them; no global flush."""
    tables = {}
    table = None
    for line in saved.splitlines():
        if line.startswith('*'):
            table = line[1:]
            tables[table] = {'owned': [], 'rules': []}
        elif table and line.startswith(':'):
            name = line.split()[0][1:]
            if name != 'DOCKER-USER' and name.startswith(CHAIN_PREFIXES):
                tables[table]['owned'].append(name)
        elif table and line.startswith('-A '):
            tables[table]['rules'].append(shlex.split(line))
    commands = []
    for table, data in tables.items():
        base = [executable, '-w', '-t', table]
        for rule in data['rules']:
            targets = [rule[i + 1] for i, token in enumerate(rule[:-1]) if token in ('-j', '-g')]
            if rule[1] not in data['owned'] and any(t in data['owned'] for t in targets):
                commands.append(base + ['-D'] + rule[1:])
        commands.extend(base + ['-F', name] for name in data['owned'])
        commands.extend(base + ['-X', name] for name in data['owned'])
    return commands
