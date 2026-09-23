import json
import os
import pathlib
import re
import shutil
import subprocess

binaries = ['kubeadm', 'kubelet', 'kubectl', 'containerd', 'ctr', 'crio', 'docker', 'dockerd', 'podman', 'conmon', 'runc', 'crun', 'cilium']
packages = set(binaries + ['kubernetes-cni', 'cri-tools', 'containers-common', 'containers-common-extra', 'netavark', 'aardvark-dns', 'containernetworking-plugins'])
roots = ['/etc/kubernetes', '/var/lib/kubelet', '/var/lib/etcd', '/etc/cni/net.d', '/opt/cni/bin', '/var/lib/cni', '/etc/containerd', '/var/lib/containerd', '/run/containerd', '/etc/containers', '/var/lib/containers', '/run/containers', '/run/libpod', '/var/lib/cilium', '/run/cilium', '/var/log/pods', '/var/log/containers', '/opt/containerd', '/run/runc', '/run/crun', '/root/.kube/config', '/sys/fs/bpf/cilium']
processes = []
for p in pathlib.Path('/proc').glob('[0-9]*'):
    try:
        name = (p / 'comm').read_text().strip()
        cgroup = (p / 'cgroup').read_text()
        if name.startswith(('kube-', 'containerd', 'cilium')) or name in binaries + ['etcd', 'pause', 'agnhost'] or re.search(r'kubepods|libpod-[0-9a-f]|cri-containerd-|/docker/', cgroup):
            processes.append({'pid': int(p.name), 'name': name})
    except (FileNotFoundError, ProcessLookupError):
        pass
installed = set(subprocess.check_output(['rpm', '-qa', '--qf', '%{NAME}\n'], text=True).splitlines())
links = json.loads(subprocess.check_output(['ip', '-j', 'link', 'show'], text=True))
remaining_links = [x['ifname'] for x in links if x['ifname'].startswith(('cilium_', 'lxc', 'cali', 'flannel.', 'cni-podman')) or x['ifname'] in ['cni0', 'podman0', 'docker0']]
mounts = [line for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if any(root in line for root in roots if root != '/root/.kube/config')]
listening = subprocess.check_output(['ss', '-H', '-lntp'], text=True)
ports = [line for line in listening.splitlines() if re.search(r':(6443|2379|2380|10250|10257|10259)\s', line)]
result = {
    'remaining_processes': processes,
    'remaining_binaries': [name for name in binaries if shutil.which(name)],
    'remaining_packages': sorted(installed & packages),
    'remaining_paths': [root for root in roots if os.path.lexists(root)],
    'remaining_interfaces': remaining_links,
    'remaining_mounts': mounts,
    'remaining_kubernetes_ports': ports,
    'unrelated_sentinel_preserved': pathlib.Path('/srv/uninstall-preserve-test/keep').read_text() == 'preserve-test\n',
    'ssh_listening': bool(re.search(r':22\s', listening)),
    'boot_id': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
}
print(json.dumps(result, indent=2))
assert all(not value for key, value in result.items() if key.startswith('remaining_')), 'Teardown left resources behind'
assert result['unrelated_sentinel_preserved'] and result['ssh_listening']
