# Single-node install and full-uninstall live test, 2026-09-22

**Result: passed after correcting issues found by the live test.** Host `10.0.0.186` (`k8s-master`, SSH user `alan`) is left with Kubernetes and the tested container runtimes removed. It rebooted successfully and remains accessible over SSH. A second uninstall completed with **zero changes**.

## Environment and scope

| Component | Tested value |
| --- | --- |
| OS | Fedora Linux 44 Cloud Edition, x86_64 |
| Kernel | 6.19.10-300.fc44.x86_64 |
| Resources | 10 CPUs, approximately 24 GiB RAM, 120 GiB root disk |
| Controller | Ansible core 2.20.7 |
| Kubernetes control plane | 1.36.2 |
| kubeadm / kubelet / kubectl packages | 1.36.4, selected by the existing minor-version RPM repository |
| containerd | 2.2.2, upstream binaries |
| runc | 1.2.2, upstream binary |
| Cilium | 1.19.6, Kubernetes IPAM |
| CNI plugin binaries | 1.9.1 |
| Podman / crun | 5.8.1 / 1.27, preinstalled RPMs |

The host initially had no Kubernetes installation and no Podman containers/images. Passwordless sudo was available. The SSH key is excluded from Git and collection build artifacts; its contents were never logged.

The existing `playbooks/k8s-single-node.yml` was used. Test overrides were:

```yaml
cni_version: '1.9.1'
k8s_container_runtime: containerd
container_storage_path: /var/lib/containerd
k8s_selinux_state: permissive
cilium_gateway_api_enabled: false
k8s_uninstall_hosts: k8s_cluster
k8s_uninstall_confirmation: REMOVE-ALL-CONTAINERS
```

CNI binaries were overridden because the existing `1.20.1` pin has no matching upstream release. Containerd used its own data root instead of sharing Podman's `/var/lib/containers` tree. This test did not implement the separate stack-version upgrade plan.

## Verified behavior

1. The single-node installer completed (`ok=143`, `changed=43`, `failed=0`). Node readiness, etcd health and all system pods were verified. Cilium IPAM was corrected as described below before application checks.
2. The [Kubernetes smoke workloads](../../tests/integration/uninstall/workloads.yml) became Ready. A client reached the web service by its full name, `web.uninstall-smoke.svc.cluster.local`, and read an `emptyDir` marker. This exercised cluster DNS, service routing, pod networking and local pod storage.
3. A Podman container named `uninstall-podman-smoke` ran with a named volume containing a verified marker. A separate containerd task named `uninstall-standalone` ran in the `default` namespace, outside Kubernetes's `k8s.io` namespace.
4. A marker was created in `/var/lib/containerd`. A symlink beneath `/var/lib/kubelet` pointed to a sentinel outside the removal roots, at `/srv/uninstall-preserve-test/keep`.
5. Uninstall `--check` passed (`ok=9`, `changed=0`, `failed=0`). After preview, the Kubernetes service still responded, the Podman volume marker was readable, and the standalone containerd task was running.
6. Full uninstall terminated workloads and erased local state. The first attempt reached package removal, where a Fedora dependency issue stopped the run. After the package-list fix, retry completed (`ok=26`, `changed=5`, `failed=0`) and rebooted the host.
7. The independent [Fedora host verification script](../../tests/integration/uninstall/verify_fedora_host.py) checked live processes, executables on PATH, installed RPMs, data paths, mounts, network interfaces, BPF state and listening Kubernetes ports. Every remaining-resource list was empty. SSH remained available, and the external sentinel was preserved.
8. A second full uninstall, without another reboot, passed with `ok=22`, **`changed=0`**, `failed=0`. The preserved sentinel was checked again and then removed as test-fixture cleanup.

## Issues found and corrected

- **Cilium ignored the configured pod subnet.** Its default cluster pool was `10.0.0.0/8`, overlapping this host's `10.0.0.0/16` LAN. The installer now passes `--set ipam.mode=kubernetes`, honoring kubeadm's assigned `10.244.0.0/24` node range. On the already-created test cluster, the equivalent Cilium upgrade and component/CoreDNS restarts applied this setting; Ready pods and successful service requests then confirmed it. A regression test verifies the emitted installation option. A second fresh installation was not run.
- **Conmon's wrapped exit command confused preflight.** The parser interpreted `--exit-command-arg` as a storage path after finding a wrapped `--root`. It now decodes Podman's actual arguments, retaining custom-root validation. Regression coverage includes both separate and `--flag=value` forms.
- **Podman runtime state needed cleanup.** `/run/libpod` is now included in the guarded data-root list.
- **Fedora container-support dependencies blocked DNF5.** `containers-common-extra` required `netavark`, preventing removal of the selected runtime packages. The explicit removal list now includes `containers-common` and `containers-common-extra`. The live retry verified this fix.

The containerd API cleanup encountered an already-removed task. Its warning triggered the intended offline fallback; mandatory process/storage verification and the independent post-reboot checks both passed. `crictl` was absent on this host, so teardown also exercised containerd cleanup without CRI tooling.

The final local suite passed **34 tests**, including the new Cilium and conmon regressions. A focused independent review found no concrete regression in the live-test fixes.

## Limits and retained host state

This validates one Fedora 44 host with containerd/runc, Cilium and Podman/crun. It does not establish Docker, CRI-O, rootless, Debian-family, source-build, custom-storage or remote-PV teardown coverage. Direct standalone runc containers were not created; the Podman container exercised crun-managed state.

Uninstall removes the cluster and runtime installations, not all installer changes to the OS. General packages, kernel/sysctl configuration and swap/SELinux settings remain; SELinux is permissive on this test host. External PV data and arbitrary hostPath source directories are outside the default removal scope. No user workloads or data were present at the initial baseline.

Raw controller logs are in `/tmp/platform-live-test/`: `install.log`, `preview.log`, `uninstall.log`, `uninstall-retry.log`, and `uninstall-idempotent.log`. Inventory and the test variable file are also there. These temporary files are not part of the collection artifact.
