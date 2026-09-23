# Cluster uninstall implementation plan

User-authorized scope: implement full Kubernetes removal, terminate all containers on selected nodes, and uninstall container engines and runc/crun. Implementation only; do not run teardown on the user's machines.

## Design

Add an explicit `k8s_uninstall` role and `playbooks/cluster-uninstall.yml`. Require the exact confirmation `REMOVE-ALL-CONTAINERS` for execution; `--check` previews without mutation. Target a supplied inventory group/pattern, not implicit `all`. Remove every installed supported rootful engine (containerd, CRI-O, Docker, Podman), including containers outside Kubernetes, images, and local engine volumes. Reject detected rootless engines until the operator removes them as their owners; never report full success with unhandled containers.

Stop kubelet/restart sources, remove workloads while their runtime APIs remain available, stop engines, kill remaining runtime/shim processes, unmount node/container storage deepest-first, then remove packages, binaries, configuration and data. Removal must not recurse through mounts or symlinks into external data. Custom data directories require explicit dedicated-path inputs. Remove only identifiable Kubernetes/CNI networking objects; recommend reboot for residual kernel networking state. Do not delete remote storage or arbitrary hostPath source directories.

Use a small Ansible module backed by testable Python helpers for process termination, container API cleanup, mount handling and safe path removal. Keep package removal and systemd unit orchestration in Ansible. Engine API/CNI errors warn and fall back to mandatory offline cleanup. Fail on unsupported conditions, direct OCI cleanup failures, unsafe paths, busy mounts or failed final verification; retries must work after partial removal. Omit kubeadm reset because it bypasses safe mount/symlink traversal protections.

## Tasks

- [x] Add failing behavior tests for confirmation/check mode, container cleanup, failure propagation, mount ordering, path validation and symlink protection.
- [x] Implement the node helper/module and role: preflight, workload removal, service/process shutdown, storage cleanup, package/binary removal and verification.
- [x] Add playbook, role documentation and replace the nonexistent `/root/uninstall.sh` instructions.
- [x] Run unit tests, safe Ansible confirmation/check-mode tests, syntax checks and independent code review. Do not execute destructive tests against the controller or live inventory.

## Verification limits

Automated tests use isolated filesystem fixtures and fake runtime command boundaries. They do not substitute for a disposable VM acceptance run with each real runtime. Report this limitation explicitly.

## Progress

Planning complete. Work is on `feat/cluster-uninstall`; the earlier stack-update plan remains untouched. The user explicitly requested implementation, so proceed with that authorized work and keep destructive execution gated at runtime.


Implementation and independent review complete. Added the role/playbook, Python module/helpers, 32 unit regression tests, runtime confirmation gate, preview behavior, and usage documentation. Fixed review findings for CNI API failures, imported storage roots, OCI containers without daemon ancestors, socket unit discovery, mount/symlink safety, Cilium veth peer deletion, and repository cleanup.

Validation: 32 unit tests passed; 88 YAML files parsed; uninstall playbook syntax passed; Ansible module documentation parsed; collection build succeeded. A real unconfirmed Ansible role invocation failed at its first assertion with zero changes. A safe Ansible task test verified socket inclusion and unit ordering using synthetic facts. No cluster teardown, package removal, reboot, or real runtime mutation was executed. Disposable VM acceptance remains explicitly unperformed.


## Authorized live acceptance, 2026-09-22

The user subsequently authorized a single-node install-and-teardown test on `10.0.0.186` as `alan`. That test passed, including live Kubernetes service traffic, Podman volume and standalone containerd tasks, zero-change preview, full teardown/reboot, independent host verification, and a zero-change second uninstall. The test exposed and fixed Cilium IPAM overlap, conmon option decoding, `/run/libpod` cleanup and Fedora container-support package dependencies. See [the live-test report](../../testing/2026-09-22-cluster-uninstall-fedora44.md) for evidence and coverage limits. The full multi-runtime/OS matrix remains outstanding.
