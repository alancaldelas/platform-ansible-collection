# Full Kubernetes uninstall

`k8s_uninstall` destroys the Kubernetes installation and **all rootful containers on each selected node**, including containers unrelated to Kubernetes. It removes containerd, CRI-O, Docker, Podman, runc and crun when installed, along with images, local runtime volumes, local etcd data, Kubernetes/CNI configuration and collection-installed executables. There is no backup or rollback.

## Run

Install the updated collection on the controller before using its playbook. From this checkout:

```bash
ansible-galaxy collection build --output-path /tmp
ansible-galaxy collection install /tmp/alancaldelas-kubernetes_baremetal-1.0.0.tar.gz --force
```

Preview the selected inventory group without changing the nodes:

```bash
ansible-playbook -i inventory.ini playbooks/cluster-uninstall.yml \
  -e k8s_uninstall_hosts=k8s_cluster --check
```

Execute full removal:

```bash
ansible-playbook -i inventory.ini playbooks/cluster-uninstall.yml \
  -e k8s_uninstall_hosts=k8s_cluster \
  -e k8s_uninstall_confirmation=REMOVE-ALL-CONTAINERS
```

The host pattern is required; there is no default `all`. Include every control-plane and worker node to remove the whole cluster. The playbook processes one node at a time and stops on failure. It does not require a working Kubernetes API. The confirmation is checked both by the role and by each mutating module invocation.

Use `-e k8s_uninstall_reboot=true` to reboot each node afterward. Reboot before reinstalling to clear residual eBPF, IPVS and other kernel networking state. Reboot is not enabled by default.

## Requirements and scope

- Linux nodes with systemd, Debian/Ubuntu or RedHat-family package management, root access through Ansible `become`, and `umount`.
- Ansible core 2.15 or newer. TOML storage inspection needs Python 3.11+ or `tomli` installed for the node's Ansible Python interpreter.
- Supported installations use this collection's normal package names and `/usr/local/bin`, `/usr/local/sbin` or `/opt/bin` binary locations. Remaining executables on PATH cause verification to fail with their names.
- Containerd tasks are removed across all namespaces, not only `k8s.io`. Docker/Podman containers outside Kubernetes are also removed. Direct runc/crun containers in `/run/runc` and `/run/crun` are explicitly killed and deleted; custom standalone OCI state roots require separate removal before running this role.
- Pod network namespaces mounted under `/run/netns` (CNI, CRI-O and Podman names), CNI-owned interfaces including Cilium `lxc*` veths, and Cilium's pinned BPF maps and links under `/sys/fs/bpf` are removed even when the runtime API cleanup was unavailable. Verification fails if any remain.
- A listed package that other installed software still requires, such as `containers-common` when `skopeo` is installed, is kept and reported in the scope output as `packages_kept_for_other_software`, because `dnf` through Ansible will not cascade the removal onto unlisted packages. Remove that software first if the package must go.
- Detected rootless engines or default rootless storage cause preflight to refuse removal. Remove those installations as their owning users first. Custom rootless paths cannot be reliably discovered by this rootful workflow.
- Disable external automation and custom container restart services before running. Add known custom units to `k8s_uninstall_extra_services`. Do not launch new containers during teardown.

## Storage and configuration

Defaults are listed in [defaults/main.yml](defaults/main.yml); the full data directory list is in [the uninstall helper](../../plugins/module_utils/uninstall.py).

Custom engine storage discovered through standard configuration, containerd imports, running daemon arguments, or available engine inspection must fall within the selected data roots. Otherwise preflight fails before container deletion. Explicitly add dedicated custom storage roots after reviewing them:

```yaml
# uninstall-vars.yml
k8s_uninstall_extra_data_paths:
  - /srv/container-data
  - /srv/container-snapshots
k8s_uninstall_extra_services:
  - my-container-restart.service
k8s_uninstall_kubeconfig_paths:
  - /root/.kube/config
  - /home/operator/.kube/config
```

Pass this file with `-e @uninstall-vars.yml` to both preview and execution. Custom configuration files outside the default roots also need an explicitly selected dedicated directory. Stopped engines with nonstandard configuration locations cannot be automatically discovered; supply all their dedicated storage/configuration roots. Broad system directories and symlinked roots are rejected.

Nested mounted volumes are detached before directory deletion, without traversing their contents. **A filesystem mounted exactly at a selected data root is treated as dedicated runtime storage and its contents are erased before unmounting.** Include a dedicated nested local storage filesystem as an explicit extra root if its contents must also be erased. Remote PV contents, external etcd, and bind-mount/hostPath source directories outside the selected roots are not erased. OCI bundles outside these roots are also preserved.

Only explicitly listed kubeconfig files are removed; the role does not delete users' entire `.kube` directories. It preserves general system settings, build toolchains, unrelated host firewall rules and the `DOCKER-USER` chain. It removes known Kubernetes/CNI/runtime network objects and repository entries installed by the collection; it is not an OS factory reset.

## Failure behavior

The sequence is: validate scope, stop kubelet, remove workloads using runtime APIs, stop/disable engine sockets and services, kill residual processes, unmount and erase selected state, uninstall packages and binaries, then verify removal. Process identities captured before shutdown include descendants of runtime shims; PID start times prevent killing an unrelated process that reused a PID.

Engine API or CNI cleanup errors produce warnings and fall back to mandatory local cleanup. Direct OCI runtime cleanup errors, unsafe paths, busy mounts, surviving processes, remaining packages or remaining executables stop the run. No lazy unmount or global firewall flush is used. `kubeadm reset` is deliberately omitted because its recursive cleanup bypasses this role's mount and symlink protections.

A failed run may have already removed workloads or data. Resolve the reported condition and rerun with the same explicit scope; absent packages, files and services are tolerated. This is whole-cluster destruction, not a procedure for safely removing one member from a cluster that must remain operational.

## Validation

Run safe unit tests on the controller:

```bash
python3 -m unittest discover -s tests/unit -v
```

Tests use temporary directories and mocked runtime/process boundaries. They cover confirmation/check mode, all containerd namespaces, direct OCI cleanup, imported storage settings, PID reuse, orphaned processes, mount ordering, symlink protection, scoped firewall cleanup and failure propagation. No real node teardown is performed by this suite.

The [Fedora 44 live-test report](../../docs/testing/2026-09-22-cluster-uninstall-fedora44.md) records a successful single-node Kubernetes/containerd/Cilium installation, application networking checks, Podman/crun volume and standalone containerd workloads, read-only preview, full teardown, reboot and independent host verification. The test exposed and corrected conmon argument parsing and Fedora container-package dependency handling.

The full cross-platform acceptance matrix remains outstanding: repeat on disposable VMs for every engine and both package/source installation methods, including custom storage, mounted remote volumes, stopped containers and socket activation. This one host test does not establish Docker, CRI-O or Debian coverage.
