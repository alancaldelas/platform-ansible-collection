# Kubernetes, CNI, and Runtime Updates Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task. Use `superpowers:subagent-driven-development` only if that execution method is selected. Track execution with the checkboxes below.

**Goal:** Update every advertised CNI and runtime to verified stable releases, make installation and upgrade behavior honor those versions, and provide a tested route to the latest Kubernetes release.

**Architecture:** Keep the existing Ansible collection and role boundaries. Add explicit component versions and compatibility checks, split the large CNI task file by provider, and make `cluster_upgrade` coordinate safe cluster-wide phases using the existing node upgrade role. Installation roles reconcile fresh hosts; disruptive changes to existing Kubernetes nodes go through the upgrade orchestrator.

**Tech Stack:** Ansible, YAML/Jinja, kubeadm, systemd, containerd/runc, CRI-O, Docker/cri-dockerd, Podman, Cilium, Calico, Flannel, Multus.

**Spec:** The user's request to review this repository and plan updates, clarified to include **every CNI and runtime**; the Scope and Global Constraints sections below are the implementation requirements.

**Status:** Planning only. No role, playbook, inventory, or cluster configuration was changed. Release research and repository checks were performed on 2026-09-22 against commit `f594ba8`.

## Scope and recommended release strategy

Cover fresh installations, repeat runs, and upgrades for containerd, CRI-O, Docker, Podman, Cilium, Calico, Flannel, and Multus. Cover Weave explicitly through retirement and migration because its original upstream is archived. Include the supporting CNI reference binaries, runc, Cilium CLI, cri-dockerd, Gateway API, and source-build toolchains.

There is no single currently documented configuration containing the latest Kubernetes release and all these providers. Kubernetes **1.37.0** is available, but Cilium 1.20's published tested range ends at 1.36 and Calico 3.32 lists 1.34–1.36. This is a support-evidence gap, not proof that 1.37 cannot work. [Kubernetes release](https://github.com/kubernetes/kubernetes/releases/tag/v1.37.0), [Cilium compatibility](https://docs.cilium.io/en/stable/network/kubernetes/compatibility/), [Calico requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements).

Recommended approach:

1. Repair correctness and upgrade safety before promoting new defaults.
2. Establish Kubernetes **1.36.4** as the common validation baseline, with current stable CNI releases and compatible runtimes. containerd **2.3.5 LTS** is the documented runtime bridge.
3. Validate containerd **2.4.0** and Kubernetes **1.37.0** as explicit latest-release profiles. Promote each provider/runtime combination separately when its compatibility and acceptance gates pass. Keep unqualified combinations visibly experimental, with an explicit opt-in; do not call the entire collection 1.37-supported on the strength of one successful provider.
4. Recheck releases immediately before implementation and refresh exact pins and evidence together. A scheduled release date is not evidence of a published artifact.

Kubernetes patch pages currently list 1.36.4 and 1.35.8, with 1.36.5 and 1.35.9 still described as next releases. containerd's compatibility table lists 2.3 for Kubernetes 1.36 and 2.3/2.4 for 1.37. [Kubernetes patch history](https://kubernetes.io/releases/patch-releases/), [containerd releases and compatibility](https://github.com/containerd/containerd/blob/main/RELEASES.md), [containerd 2.3.5](https://github.com/containerd/containerd/releases/tag/v2.3.5).

Alternatives considered: a simultaneous version-only bump leaves known installation and upgrade failures intact; retaining only Cilium/containerd would reduce work but conflicts with the clarified scope. The staged approach preserves the scope while making support claims measurable.

## Global Constraints

- Cover every advertised CNI and runtime; do not silently remove an option or substitute a different provider.
- Pin stable releases, package versions, manifests, and container images. No `latest`, `main`, or `snapshot` artifact selectors in supported deployment paths.
- Keep existing public variable names working through explicit aliases; reject conflicting old and new values.
- Preserve operator overrides, registry settings, pod/service CIDRs, CNI installation method, and ramdisk `NoPivotRoot` behavior.
- Kubernetes upgrades advance one minor at a time; complete all nodes in one hop before the next hop.
- Cilium upgrades advance one minor at a time after updating the source minor to its latest patch. containerd follows supported sequential minor or documented sequential LTS paths.
- Failed drain, invalid backup, unhealthy CRI, or failed network verification stops the rollout. A failed node stays cordoned.
- Do not use a normal install rerun to change a live cluster's Kubernetes minor, CNI provider, or container runtime family.
- Podman is a standalone engine, not a kubelet CRI endpoint. Docker requires cri-dockerd when selected for Kubernetes.
- Linux amd64 and arm64 are the initial artifact architectures. Reject other architectures before mutation until their artifacts and tests are added.
- Validate distribution-specific packages and prerequisites; a broad OS-family match is not a compatibility guarantee.
- Production deployment, CNI migration, and recovery require actual inventory and workload information; this plan does not authorize running them against the existing inventory.

## Review findings

Severity is relative to this update. Line references describe the reviewed commit.

| Priority | Finding and evidence | Effect | Task |
| --- | --- | --- | --- |
| P1 | `roles/runtime/defaults/main.yml:14` sets `cni_version: 1.20.1`; `roles/runtime/tasks/containerd.yml:115` uses it for `containernetworking/plugins`. The upstream release API returns HTTP 404 for that tag. | Default containerd provisioning cannot download its reference CNI bundle. This is unrelated to the Cilium version. | 1, 2 |
| P1 | `roles/k8s_upgrade/tasks/preflight_apis.yml:26` and `preflight_flags.yml:16` unconditionally load hop-specific files. Only 1.33→1.34 and 1.34→1.35 files exist. | Existing 1.35→1.36 playbooks fail before upgrade; 1.34→1.35 data still contains unreviewed empty templates. | 9 |
| P1 | `roles/cluster_upgrade/tasks/upgrade_workers.yml:26` ignores failed drains, uses inventory names as Kubernetes names, and uncordons without a Ready/version gate. | A PDB or drain failure does not prevent node mutation; aliases can target the wrong name. | 9 |
| P1 | `roles/k8s_upgrade/tasks/snapshot.yml:65` moves the snapshot, then line 95 verifies the old pod path and line 112 suppresses failure. Only nonzero file size is required afterward. | A corrupt snapshot can pass the supposed mandatory integrity gate. The first etcd pod is also not guaranteed to reside on the host where the file is moved. | 9 |
| P1 | `roles/runtime/tasks/docker.yml:32` references missing `docker-daemon.json.j2`; `podman.yml:21` and `:28` reference missing `registries.conf.j2` and `storage.conf.j2`. | Docker and Podman installation fail during templating. Syntax checks do not catch this. | 5, 6 |
| P1 | `roles/runtime/templates/crio.conf.j2:150` renders the default as `log_size_max = 10Mi`. Default rendering fails TOML parsing. It also inherits Docker's `overlay2` storage setting. | CRI-O cannot reliably start with the defaults. | 4 |
| P1 | `roles/cluster_upgrade/defaults/main.yml:7–8` self-reference `k8s_cni_plugin` and `cilium_version`. A local Ansible evaluation reproduced a recursive-template error. | Direct role usage fails unless callers override the values. | 1 |
| P1 | `playbooks/cluster-upgrade.yml` targets `all` with `serial: 1`; `roles/cluster_upgrade/tasks/main.yml` handles only master/worker, upgrades Cilium after each master, and never upgrades runtimes. | Serial order does not establish primary/additional-control-plane/worker phases. Additional control planes and runtime updates are not correctly coordinated. | 9 |
| P2 | `roles/k8s/tasks/system_validation.yml:104–134` checks binary presence, then `roles/k8s/tasks/main.yml` skips runtime management when installed. Source builds use `creates` on the installed binary; containerd binary extraction has no restart notification. | Version changes can be skipped or leave the old daemon running. Deleting download caches also causes redundant extraction on reruns. | 2, 9 |
| P2 | `roles/k8s/tasks/kubernetes_install.yml:76–109` installs unversioned packages; its Debian repository block only matches Ubuntu. `kubeadm-config.yaml.j2` still uses v1beta3. | Requested patch and installed components can disagree; Debian support is incomplete. Update and validate kubeadm schema together with argument shape. | 3 |
| P2 | `roles/k8s/tasks/cni_install.yml:51` treats pod presence as desired-version satisfaction. CLI downloads float; readiness errors are ignored. Flannel is checked in `kube-system`, while its current manifest uses `kube-flannel`. | Install reruns do not perform controlled CNI updates and can report success after failed rollout checks. | 7, 8 |
| P2 | The pinned Multus v4.3.1 upstream thick manifest contains `snapshot-thick` in both image references. Current code applies the downloaded manifest without rewriting images. | A tagged manifest URL alone does not make installation reproducible. | 8 |
| P2 | CRI-O uses legacy `devel:kubic` repositories and derives `crio_version` by appending `.0` to `kubernetes_version`. Docker/Podman ignore the advertised version input. | Full Kubernetes patches can produce invalid CRI-O versions; installed engine versions depend on repository state. | 1, 4, 5, 6 |
| P2 | Runtime downloads and Go archives hard-code amd64; Go defaults to 1.21.3; docs advertise kernel 4.15. | Current source tags need newer Go; arm64 downloads are incorrect; current Cilium/Calico prerequisites are understated. | 1–4, 10 |
| P2 | Examples override defaults with Kubernetes 1.28/1.33, containerd 1.7.2, and runc 1.1.9. Tests are localhost role invocations; there is no repository CI workflow. | Updating defaults alone leaves documented entrypoints stale, without behavioral coverage. | 10 |

### Checks performed during review

- Parsed all **81** YAML files under `roles/` and `playbooks/`: passed.
- Ran `ansible-playbook --syntax-check` on all **27** playbooks using a temporary collection layout and local inventory: passed, with Ansible core **2.20.7**.
- Reproduced the recursive Cilium default using a localhost play that only loads variables and evaluates them: failed as described, zero changes.
- Rendered runtime templates with their defaults and parsed TOML: containerd syntax passed; CRI-O failed on `10Mi` after supplying the Ansible `to_json` equivalent to Jinja.
- Checked official release pages and GitHub release/content APIs, including the missing reference-CNI tag and floating Multus image references.
- No node connections, package installs, deployment playbooks, network conformance tests, or live upgrades were run. Syntax success does not establish deployability.

## Release inventory and disposition

These are dated research results, not runtime lookups to embed in Ansible. Package availability for each target distribution still needs qualification.

| Component | Repository state | Verified target | Disposition |
| --- | --- | --- | --- |
| Kubernetes | Default 1.35.3; some single-node examples 1.36.2; many examples 1.28 | [1.37.0](https://github.com/kubernetes/kubernetes/releases/tag/v1.37.0) | Latest target; 1.36.4 common validation baseline pending provider qualification |
| containerd | 2.2.2; examples 1.7.2 | [2.4.0](https://github.com/containerd/containerd/releases/tag/v2.4.0) | Target; 2.3.5 LTS is the intermediate/support baseline |
| runc | 1.2.2; examples 1.1.9 | [1.5.1](https://github.com/opencontainers/runc/releases/tag/v1.5.1) | Pin for independently managed containerd installations; respect package ownership elsewhere |
| CNI reference plugins | Invalid 1.20.1 | [1.9.1](https://github.com/containernetworking/plugins/releases/tag/v1.9.1) | Separate variable from network-provider versions |
| Cilium | 1.19.6; upgrade example 1.20.1 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | Stage through 1.19.8; tested Kubernetes ceiling 1.36 |
| Cilium CLI | Floating latest | [0.20.0](https://github.com/cilium/cilium-cli/releases/tag/v0.20.0) | Pin and checksum independently |
| Gateway API | v1.4.1 | [v1.6.1 required by Cilium 1.20](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/) | Conditional upgrade; preserve existing TLSRoute stored versions |
| Calico | 3.25.0 | [3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2) | Keep current manifest installation method; tested Kubernetes ceiling 1.36 |
| Flannel | Floating latest | [0.28.9](https://github.com/flannel-io/flannel/releases/tag/v0.28.9) | Pin release manifest and all images; verify provider-specific readiness |
| Weave | 2.8.1 | No maintained target in [archived upstream](https://github.com/weaveworks/weave) | Detect existing installations; block new latest-stack deployments and provide replacement-cluster migration |
| Multus | v4.1.4 | [v4.3.1](https://github.com/k8snetworkplumbingwg/multus-cni/releases/tag/v4.3.1) | Pin both thick-plugin images to release tags/digests; validate with each primary CNI |
| CRI-O | Derived from Kubernetes 1.28; obsolete repo scheme | [1.37.1](https://github.com/cri-o/cri-o/releases/tag/v1.37.1) | Pair with Kubernetes 1.37; use [1.36.6](https://github.com/cri-o/cri-o/releases/tag/v1.36.6) for the 1.36 baseline |
| Docker Engine | Example 24.0.7; actual packages unpinned | [29.8.1](https://docs.docker.com/engine/release-notes/29/) | Update standalone support and implement a tested Kubernetes adapter path |
| cri-dockerd | Missing | [0.4.4](https://github.com/Mirantis/cri-dockerd/releases/tag/v0.4.4) | Required for Docker-backed kubelets; explicit CRI socket |
| Podman | Example 4.6.0; actual distro package unpinned | [6.1.2](https://github.com/podman-container-tools/podman/releases/tag/v6.1.2) | Standalone only; qualify distribution packages and dependencies |

The final GitHub API check found CRI-O 1.37.1 and 1.36.6 published on September 21; the initially retrieved latest-release web result still showed 1.36.5. The explicit release records above supersede that stale result.

Source-build minimums read from tagged `go.mod` files: containerd 2.4.0 requires Go 1.26.6, containerd 2.3.5 requires 1.26.3, Kubernetes 1.36.4/1.37.0 require 1.26.0, and runc 1.5.1 requires 1.25.0. Select a current patched Go toolchain satisfying these and each project's build instructions, pin its checksum, and test builds; merely setting the lowest `go` directive is not sufficient validation. [containerd go.mod](https://github.com/containerd/containerd/blob/v2.4.0/go.mod), [Kubernetes go.mod](https://github.com/kubernetes/kubernetes/blob/v1.37.0/go.mod), [runc go.mod](https://github.com/opencontainers/runc/blob/v1.5.1/go.mod).

## Review Focus

1. Installed-version drift and interrupted reruns must converge or stop explicitly, never silently skip requested updates: Tasks 2, 3, 9.
2. A Kubernetes node name different from its inventory alias, PDB-blocked drain, or corrupt backup must prevent further mutation: Task 9.
3. Existing Gateway API TLSRoutes, Calico IPPools/OwnerReferences, and Multus attachments must survive provider updates: Tasks 7, 8.
4. Older glibc, unsupported CPU architecture, unavailable distro package, and changed storage drivers must fail before disrupting services: Tasks 1, 2, 4–6.
5. Partial cluster failures, omitted inventory groups, and direct task/tag entrypoints must not bypass ordering or verification: Tasks 9, 10.

## Implementation tasks

Each task is an independently reviewable change. Add the focused failing regression first, implement, rerun its checks, and commit the task before moving on. The code blocks specify concrete interfaces and critical behavior; the acceptance cases cover the deployed behavior as well as static rendering.

### Task 1: Define versions, compatibility, and validation contracts

**Files:** Modify `roles/runtime/defaults/main.yml`, `roles/runtime/vars/main.yml`, `roles/k8s/defaults/main.yml`, `roles/cluster_upgrade/defaults/main.yml`; create `roles/runtime/tasks/validate.yml`, `roles/k8s/tasks/validate_versions.yml`, `tests/unit/test_versions.py`, `tests/fixtures/versions.yml`, `docs/support-matrix.md`.

**Interface:** Existing inputs remain valid. Add `containerd_version`, `docker_version`, `podman_version`, `cni_plugins_version`, `cilium_cli_version`, `cri_dockerd_version`, and `k8s_allow_unverified_stack: false`. Keep `crio_version` independent from Kubernetes patch versions. A legacy `container_runtime_version` applies only to the selected runtime, and legacy `cni_version` aliases the reference binaries. Internal `_runtime_target_version` is the resolved string; `_runtime_arch` is `amd64` or `arm64`.

- [ ] Write fixtures for standalone role use, legacy-only input, new-only input, conflicting inputs, full Kubernetes patches with CRI-O, invalid CNI pins, prereleases, and unsupported architecture. Reproduce the recursive-default failure in a no-mutation localhost play.
- [ ] Replace self-referencing defaults with literals. Resolve aliases without `set_fact` overwriting public user variables. Do not give the legacy generic runtime variable a containerd-valued default that also shadows Docker or Podman.

```yaml
# Concrete defaults, independent component namespaces.
container_runtime: containerd
containerd_version: "2.4.0"
crio_version: "1.37.1"  # The Kubernetes 1.36 baseline profile overrides this to 1.36.6.
docker_version: "29.8.1"
podman_version: "6.1.2"
cni_plugins_version: "1.9.1"
runc_version: "1.5.1"
cri_dockerd_version: "0.4.4"
```

- [ ] Implement assertions for semantic versions, selected provider/runtime, CRI-O minor pairing, and published support bounds. For Kubernetes 1.37 plus Cilium/Calico require explicit experimental opt-in until qualified; Podman selection as a Kubernetes runtime always fails. A version override must not bypass prerequisite or artifact checks.
- [ ] Keep role-owned defaults canonical. Shared examples should inherit them; transitional profiles explicitly pin their complete tested tuple. Record each tuple as `documented`, `locally-tested`, or `experimental`, with source and test evidence.
- [ ] Run `python3 -m unittest discover -s tests/unit -p 'test_versions.py'` and the localhost defaults regression. Expect all alias/override cases to resolve without recursion; rejected tuples must fail before any mutating task.
- [ ] Commit: `refactor: define explicit stack versions and compatibility checks`.

### Task 2: Make containerd and reference CNI installation upgrade-aware

**Files:** Modify `roles/runtime/tasks/main.yml`, `common.yml`, `containerd.yml`, `roles/runtime/templates/containerd-config.toml.j2`, `roles/runtime/handlers/main.yml`; create `roles/runtime/tasks/cni_plugins.yml`, `roles/runtime/tasks/verify.yml`, `tests/unit/test_runtime_templates.py`, `tests/integration/runtime.yml`.

**Interface:** Consume resolved versions from Task 1. Add `runtime_change_mode: install` (`install` or `upgrade`), `runtime_backup_dir: /var/backups/container-runtime`, and `runtime_artifact_dir: /var/cache/container-runtime`. `containerd_archive_sha256` is a 64-character digest from a committed version/architecture artifact manifest, validated before downloading; add that manifest as `roles/runtime/vars/artifacts.yml`. `upgrade` is invoked only inside the drained-node transaction in Task 9. Verification produces observed daemon and OCI-runtime versions, not just on-disk executable versions.

- [ ] Add cases for fresh install, matching rerun, binary-only version change, source-version change with an existing binary, checksum failure, architecture mismatch, registry mirrors, and ramdisk mode. A second matching run must perform no extraction or restart.
- [ ] Resolve architecture before building URLs, validate checksums before extraction, and stage artifacts under versioned paths. Share CNI reference binaries with CRI-O/cri-dockerd without replacing provider-owned binaries or deleting `/etc/cni/net.d`.

```yaml
- name: Download pinned containerd archive
  ansible.builtin.get_url:
    url: "https://github.com/containerd/containerd/releases/download/v{{ _runtime_target_version }}/containerd-{{ _runtime_target_version }}-linux-{{ _runtime_arch }}.tar.gz"
    dest: "{{ runtime_artifact_dir }}/containerd-{{ _runtime_target_version }}-{{ _runtime_arch }}.tar.gz"
    checksum: "sha256:{{ containerd_archive_sha256 }}"
    mode: '0644'
```

- [ ] Read installed component versions and compare them with targets. Replace `creates: /usr/local/bin/containerd` and runc's equivalent with version-aware build/install decisions. Notify and flush a runtime restart after binary or configuration replacement; preserve old binaries/configuration for the tested recovery procedure.
- [ ] Validate the current config-v3 template against 2.3.5 and 2.4.0. Preserve `SystemdCgroup`, registry `config_path`, mirror behavior, CNI paths, sandbox image, and `NoPivotRoot`. Do not replace working settings with an unreviewed generated default.
- [ ] Check glibc before selecting upstream dynamic binaries: containerd 2.4.0's release identifies glibc 2.35. For older systems, select a separately qualified static/source artifact or fail before stopping services. Install a pinned build toolchain satisfying tagged source requirements; do not remove a host-wide Go installation unconditionally.
- [ ] In disposable VMs run `containerd --version`, `ctr version`, `crictl info`, and a sandbox/container creation test, then repeat the role. Exercise `2.2.2 → 2.2.8 → 2.3.5 → 2.4.0` as separate supported steps; test persisted containers and registry pulls after restart. Keep package-managed Docker dependencies outside this installer.
- [ ] Commit: `fix: reconcile containerd and CNI binaries by version`.

### Task 3: Pin Kubernetes packages and modernize kubeadm configuration

**Files:** Modify `roles/k8s/tasks/main.yml`, `system_validation.yml`, `kubernetes_install.yml`, `kubernetes_install_source.yml`, `kubernetes_join.yml`, `kubernetes_cp_join.yml`, `roles/k8s/templates/kubeadm-config.yaml.j2`; create `tests/unit/test_kubeadm_template.py`, `tests/integration/kubernetes-install.yml`.

**Interface:** Add `k8s_cri_socket` with a mapping for containerd, CRI-O, and cri-dockerd; use it consistently for init and joins. `kubernetes_version` denotes the full installed version for kubeadm, kubelet, kubectl, and control-plane images.

- [ ] Test rendered configs for all three Kubernetes-capable runtimes, custom node names, single-node and HA endpoints, and user overrides. Assert v1beta4 argument lists and correct sockets.

```yaml
apiVersion: kubeadm.k8s.io/v1beta4
kind: InitConfiguration
nodeRegistration:
  criSocket: "{{ k8s_cri_socket }}"
---
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
kubernetesVersion: "v{{ kubernetes_version }}"
apiServer:
  extraArgs:
    - name: bind-address
      value: "0.0.0.0"
```

- [ ] Apply the v1beta4 migration to the full template, including controller-manager and scheduler `extraArgs`. Validate using target `kubeadm config validate --config` in the integration image; preserve existing networking and HA configuration.
- [ ] Create apt keyring directories, handle Debian and Ubuntu repositories, install exact package versions with repository suffix/epoch resolution, and apply holds/versionlocks where appropriate. Verify the installed full patch matches the requested one on Debian-family and RPM-family systems.
- [ ] Separate runtime health/version inspection from binary-presence detection. A live-node mismatch routes to the upgrade playbook; an unmanaged runtime is inspected and required to meet CRI compatibility without being reconfigured.
- [ ] Validate provider-specific kernel, cgroup, and network prerequisites. Cilium requires 5.10 or documented equivalents such as RHEL 8.10's backports; Calico documents 5.10. Keep distribution-aware checks rather than comparing kernel strings alone.
- [ ] Update the source path's Go/toolchain management and full-version verification. Test a source-version change and ensure existing output files do not suppress rebuilding. Derive pause/CoreDNS/etcd images from target kubeadm rather than independent floating updates.
- [ ] Run template tests and fresh single-node/HA installs at 1.36.4, then isolated 1.37.0 experimental profiles. Verify exact package versions, CRI health, Ready nodes, and no init/join rerun on matching hosts.
- [ ] Commit: `feat: support pinned Kubernetes releases with kubeadm v1beta4`.

### Task 4: Repair and update CRI-O

**Files:** Modify `roles/runtime/tasks/crio.yml`, `roles/runtime/templates/crio.conf.j2`, `roles/runtime/defaults/main.yml`, `roles/runtime/vars/main.yml`, `playbooks/runtime-crio.yml`; create `tests/unit/test_crio_config.py`, `tests/integration/crio.yml`.

**Interface:** `crio_version: 1.37.1` and `_crio_minor: 1.37` are separate from the full Kubernetes patch; the baseline profile uses `1.36.6` and `1.36`. Add CRI-O-specific storage and log-limit inputs; retain shared variables only when their values are valid for CRI-O.

- [ ] Add a real default-template regression that currently fails:

```python
import json
import tomllib
import unittest
from pathlib import Path
import jinja2
import yaml

class CrioConfigTests(unittest.TestCase):
    def test_default_config_parses(self):
        defaults = yaml.safe_load(Path('roles/runtime/defaults/main.yml').read_text())
        env = jinja2.Environment()
        env.filters['to_json'] = json.dumps
        text = env.from_string(Path('roles/runtime/templates/crio.conf.j2').read_text()).render(**defaults)
        config = tomllib.loads(text)
        self.assertIsInstance(config['crio']['runtime']['log_size_max'], int)
        self.assertEqual(config['crio']['storage_driver'], 'overlay')
```

- [ ] Replace `devel:kubic` repositories with the current `https://download.opensuse.org/repositories/isv:/cri-o:/stable:/v{{ _crio_minor }}/{deb,rpm}/` scheme and signed keyrings. Pin actual package versions and query candidate availability before mutation. [CRI-O packaging instructions](https://cri-o.io/).
- [ ] Use numeric bytes for `log_size_max` (10 MiB is `10485760`), `overlay` for containers/storage, and runtime/conmon paths supplied by the selected package or source installation. Validate the configuration against the target CRI-O binary. Do not hard-code `/usr/local/sbin/runc` for package-managed installations.
- [ ] Include reference CNI binary provisioning independently from containerd. Avoid installing a competing default bridge conflist on Kubernetes nodes. Preserve existing CNI configuration.
- [ ] Make source rebuilds version-aware; provision CRI-O's actual dependencies and conmon/OCI runtime instead of assuming containerd's source dependencies are sufficient.
- [ ] Test CRI-O 1.36.6 with Kubernetes 1.36.4, all three maintained primary CNIs, registry pulls, log rotation, restart, and idempotency. Qualify CRI-O 1.37.1 with Kubernetes 1.37.0 in the latest profiles. Coordinate CRI-O 1.35→1.36→1.37 with the corresponding Kubernetes node transitions and keep CNI qualification gates active.
- [ ] Commit: `fix: modernize CRI-O installation and configuration`.

### Task 5: Update Docker and implement its Kubernetes adapter

**Files:** Modify `roles/runtime/tasks/docker.yml`, `roles/runtime/defaults/main.yml`, `roles/runtime/handlers/main.yml`, `playbooks/runtime-docker.yml`; create `roles/runtime/templates/docker-daemon.json.j2`, `roles/runtime/tasks/cri_dockerd.yml`, `roles/runtime/templates/cri-docker.service.j2`, `roles/runtime/templates/cri-docker.socket.j2`, `tests/unit/test_docker_config.py`, `tests/integration/docker.yml`.

**Interface:** `docker_version: 29.8.1`, `cri_dockerd_version: 0.4.4`, `docker_enable_cri: false`. The Kubernetes role sets `docker_enable_cri: true` when Docker is selected and uses `unix:///var/run/cri-dockerd.sock`.

- [ ] Add tests that the missing daemon template exists, renders valid JSON, preserves registry/mirror and logging settings, and uses the systemd cgroup driver for Kubernetes. Check standalone Docker does not install the adapter.
- [ ] Replace `apt_key`, remove the amd64-only repository selector, use distribution-appropriate Docker repositories, and install pinned `docker-ce`/CLI plus compatible package-owned dependencies. Resolve exact package release strings before the transaction.
- [ ] Implement the template with structured JSON serialization; create `/etc/docker`. Do not force a new storage driver or image-store mode onto existing Docker data. Preflight the 24→29 release changes, daemon options, storage backend, and backup/recovery; validate that source upgrade explicitly in a VM.
- [ ] Download checksum-verified cri-dockerd and install version-matched service/socket units. Configure CNI directories and pause image; wait for `crictl --runtime-endpoint unix:///var/run/cri-dockerd.sock info` before kubeadm. Docker alone is not a CRI implementation. [Kubernetes runtime documentation](https://kubernetes.io/docs/setup/production-environment/container-runtimes/).
- [ ] Validate Docker server version, pull/run/restart/volume persistence, and Kubernetes joins with the adapter. Exercise Cilium, Calico, and Flannel using the compatibility baseline, then latest-profile qualification. Do not overwrite Docker's bundled/package-owned containerd with Task 2's independent binaries.
- [ ] Commit: `feat: update Docker and add cri-dockerd integration`.

### Task 6: Update Podman as a standalone engine

**Files:** Modify `roles/runtime/tasks/podman.yml`, `roles/runtime/tasks/main.yml`, `roles/runtime/handlers/main.yml`, `roles/runtime/defaults/main.yml`, `roles/runtime/vars/main.yml`, `playbooks/runtime-podman.yml`; create `roles/runtime/templates/registries.conf.j2`, `roles/runtime/templates/storage.conf.j2`, `tests/unit/test_podman_config.py`, `tests/integration/podman.yml`.

**Interface:** `podman_version: 6.1.2`, `podman_api_enabled: false`, Podman-specific storage settings defaulting to `overlay`. A rootful API socket is enabled only when requested; daemonless use has no service-start requirement.

- [ ] Test TOML rendering, registries, insecure registries/mirrors, storage path, daemonless mode, optional socket mode, and rejection from `k8s_container_runtime`.
- [ ] Pin the Podman package to an exact available build, including required Netavark/Aardvark DNS/OCI-runtime dependencies from the qualified repository. Verify candidate availability per distribution; if 6.1.2 is unavailable, fail with the requested and available versions before changes. Document a required OS/repository update rather than silently installing an older release. [Podman installation](https://podman.io/docs/installation).
- [ ] Create the missing templates, remove the unconditional `podman.service` enable/restart, and manage `podman.socket` only for API mode. Avoid changing an existing storage driver or backend in place. Make registry/storage configuration parsing a required pre-service check.
- [ ] Rehearse 4.6→6.1.2 with persisted images and volumes. Inventory old CNI-based networks; recreate/migrate their definitions through the documented Netavark path in the maintenance window and verify DNS/network aliases. Do not confuse these standalone networks with Kubernetes primary CNI updates.
- [ ] Run `podman version`, `podman info --format json`, container creation, volume persistence, DNS between containers, and socket API checks when enabled. Repeat installation and verify no false service restarts.
- [ ] Commit: `fix: update Podman and support daemonless configuration`.

### Task 7: Unify Cilium install and upgrade behavior

**Files:** Modify `roles/k8s/tasks/cni_install.yml`, `roles/k8s/defaults/main.yml`, `roles/cluster_upgrade/tasks/upgrade_cilium.yml`; create `roles/k8s/tasks/cni/cilium.yml`, `roles/k8s/tasks/cni/gateway_api.yml`, `roles/k8s/templates/cilium-values.yaml.j2`, `tests/unit/test_cilium_values.py`, `tests/integration/cilium.yml`.

**Interface:** `cni_operation: install` (`install` or `upgrade`) selects intent. Use one structured values template for both paths. Pin CLI separately; cluster upgrade invokes this provider path once, delegated to the primary control plane. Runtime/kernel gates run before provider changes.

- [ ] Add tests for matching installed version, missing CLI on an existing cluster, version drift, exported user values, Gateway enabled/disabled, and Multus enabled/disabled. Replace pod-presence-only satisfaction with observed release/version checks.
- [ ] Install checksum-verified Cilium CLI 0.20.0 on the correct architecture for both install and upgrade. Export installed Helm user values and Cilium/Gateway resources before changes; merge reviewed values for the new chart without blindly reusing obsolete keys.
- [ ] Implement `1.19.6 → 1.19.8 → 1.20.2`, running Cilium preflight and readiness/connectivity at each step. Preserve IPAM, pod CIDR, kube-proxy mode, routing, MTU, and existing custom configuration; set `upgradeCompatibility` appropriately. Flag unsupported policy fields and CiliumNodeConfig API versions before changing agents.
- [ ] For Gateway installations, back up route objects and inspect CRD `storedVersions` before updating to v1.6.1. Existing v1alpha2 TLSRoute storage requires the compatible experimental TLSRoute CRD during migration; do not replace it directly with a standard CRD that drops that version. Upgrade Gateway API before Cilium 1.20. [Cilium upgrade guidance](https://docs.cilium.io/en/stable/operations/upgrade/).
- [ ] Preserve host-network Gateway settings and Envoy privileged-port capabilities; supply a directly reachable API endpoint when kube-proxy replacement requires it. For Multus, configure Cilium to preserve other CNI configs (`cni.exclusive: false`) and validate the resulting primary delegate.
- [ ] Fail on Cilium/operator/Envoy rollout timeout. Run `cilium status --wait`, `cilium connectivity test`, DNS, service traffic, allow/deny policies, and existing HTTP/TLS Gateway routes before continuing the cluster upgrade.
- [ ] Commit: `feat: reconcile Cilium and Gateway API upgrades safely`.

### Task 8: Update Calico, Flannel, Multus, and handle Weave retirement

**Files:** Modify `roles/k8s/tasks/cni_install.yml`, `roles/k8s/defaults/main.yml`, `playbooks/k8s-calico-cni.yml`, `k8s-flannel-cni.yml`, `k8s-weave-cni.yml`; create `roles/k8s/tasks/cni/calico.yml`, `flannel.yml`, `multus.yml`, `weave.yml`, `roles/cluster_upgrade/tasks/upgrade_cni.yml`, `tests/unit/test_cni_manifests.py`, `tests/integration/cni.yml`, `docs/weave-migration.md`.

**Interface:** All maintained providers implement `cni_operation` from Task 7 with version detection, backup, apply, and mandatory readiness. Multus is a secondary-CNI layer, not a selectable primary provider. Selecting a different primary provider on an existing cluster returns a migration-required error.

- [ ] Test generated artifact URLs, namespaces, workload selectors, embedded image references, matching reruns, existing-provider mismatch, and CIDR preservation. Ensure no rendered manifest contains `latest` or `snapshot` images.

```yaml
# Correct pinned Flannel URL; the old latest/download shape cannot simply take a tag.
flannel_manifest_url: "https://github.com/flannel-io/flannel/releases/download/v{{ flannel_version }}/kube-flannel.yml"
cni_workloads:
  calico: {namespace: kube-system, daemonset: calico-node}
  flannel: {namespace: kube-flannel, daemonset: kube-flannel-ds}
  cilium: {namespace: kube-system, daemonset: cilium}
  multus: {namespace: kube-system, daemonset: kube-multus-ds}
```

- [ ] Update Calico to 3.32.2 using its existing manifest installation method. Export policies, IPPools, BGP configuration, and customized manifest settings; apply required CRDs and retain CIDRs/encapsulation/MTU. Handle pre-3.28 OwnerReferences as documented. Rehearse 3.25→3.32 rather than inventing a universal one-minor rule; upstream describes upgrades from 3.15 onward. Keep any operator migration separate. [Calico upgrade procedure](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade).
- [ ] Pin Flannel 0.28.9, including its release-specific `flannel-cni-plugin` image. Preserve existing net-conf, backend, and MTU. Detect and handle older namespace layouts explicitly to avoid running two Flannel DaemonSets. Require rollout success in `kube-flannel`.
- [ ] Update Multus to 4.3.1 and rewrite **both** thick-daemon image references to a verified release image/digest; a release-tagged YAML file is insufficient. Preserve NetworkAttachmentDefinitions and delegated CNI ordering, binaries, and host paths. Check Cilium coexistence and CRI-O/cri-dockerd paths.
- [ ] Implement a Weave guard that reports the archived provider and stops latest-stack install/upgrade before mutation. Leave existing network state intact. Document replacement-cluster migration: export workloads and policies, recreate equivalent networking on the chosen maintained CNI, migrate persistent data, verify policy behavior and connectivity, cut over traffic, and retain the source cluster for rollback. Do not automatically substitute a fork or apply another CNI on top.
- [ ] Run per-provider install and upgrade tests with all Kubernetes-capable runtimes; verify DNS, cross-node pod traffic, ClusterIP/NodePort, MTU, and allow/deny policy for Calico/Cilium. Flannel alone does not supply NetworkPolicy enforcement, so record that limitation rather than claiming a policy test passed. For each primary provider, add a Multus secondary interface and verify connectivity after upgrades and restarts.
- [ ] Commit: `feat: update alternative CNIs and document Weave migration`.

### Task 9: Repair backup gates and orchestrate safe cluster upgrades

**Files:** Modify `roles/cluster_upgrade/tasks/main.yml`, `upgrade_workers.yml`, `roles/k8s_upgrade/tasks/main.yml`, `preflight_version.yml`, `preflight_apis.yml`, `preflight_flags.yml`, `snapshot.yml`, `upgrade_control.yml`, `upgrade_additional_cp.yml`, `playbooks/cluster-upgrade.yml`, and existing version-hop playbooks; create `roles/cluster_upgrade/tasks/upgrade_runtime.yml`, `verify_cluster.yml`, hop maps for 1.35→1.36 and 1.36→1.37, `playbooks/k8s-upgrade-1.36-to-1.37.yml`, `playbooks/k8s-upgrade-single-node-1.36-to-1.37.yml`, `tests/integration/upgrade-failures.yml`, `docs/upgrade-recovery.md`.

**Interface:** Keep explicit `k8s_upgrade_from`, `k8s_upgrade_to`, `k8s_upgrade_target_version`. Add `k8s_upgrade_node_name` defaulting to `ansible_facts['nodename']`, validated against the live node object. Runtime/CNI target versions use Task 1's contracts. Every disruptive entrypoint validates its prerequisites itself.

- [ ] Add failure-injection tests: PDB blocks drain; inventory alias differs from node name; selected etcd pod resides on another host; nonempty snapshot is corrupt; worker is NotReady; one additional control plane fails; target package is unavailable; run is interrupted after primary upgrade; caller uses `--tags upgrade` without a valid backup.
- [ ] Populate hop maps from release-specific deprecation/changelog/flag evidence. Audit the existing empty 1.34→1.35 maps too. Track an explicit reviewed status and references; an empty but unreviewed list must not imply safe. Verify the pinned Pluto release knows the target Kubernetes version, or use reviewed built-in data.
- [ ] Fix snapshot locality by selecting the etcd pod on the intended node. Verify integrity using compatible `etcdutl snapshot status` at an accessible path before/after the move, require command success and usable metadata, then fetch the snapshot and PKI backup off-node for production. Exercise an isolated restore; file size is not integrity validation. Preserve workload/PV backups separately.
- [ ] Use explicit plays in this order: discover/validate all nodes and artifact availability; backup and CNI bridge when needed; primary control plane; additional control planes with `serial: 1`; workers with `serial: 1`; final cluster verification. Set `any_errors_fatal: true` at phase boundaries and require a success marker from preceding phases so later plays cannot proceed after failure.
- [ ] Gate every node transaction on drain success. Configure force/delete-emptydir flags as explicit operator policy rather than unconditional data-loss choices. Drain before a kubelet minor update; single-node operation requires a declared outage window and workload handling. Keep runtime update and Kubernetes update as separate verified transactions when compatibility permits.

```yaml
- name: Drain the verified Kubernetes node
  ansible.builtin.command:
    argv:
      - kubectl
      - drain
      - "{{ k8s_upgrade_node_name }}"
      - --ignore-daemonsets
      - "--timeout={{ k8s_upgrade_drain_timeout }}"
  delegate_to: "{{ groups[k8s_upgrade_primary_group][0] }}"
  environment:
    KUBECONFIG: /etc/kubernetes/admin.conf
  changed_when: true
# No ignore_errors. Mutation follows only after success.
```

- [ ] After mutation require CRI health, kubelet service health, exact node version, node Ready, CNI readiness, and an actual pod sandbox/network check **before** uncordon. Keep the failing node cordoned; rescue collects diagnostics and stops, rather than unconditionally uncordoning in `always`.
- [ ] Make resumability inspect each node and completed phase: a primary already at target must not cause source-version preflight to reject unfinished workers, and an exact-version rerun must not repeat `kubeadm upgrade apply`. Permit explicit same-minor patch updates while rejecting downgrades and skipped minor hops.
- [ ] Rehearse 1.35.3→1.35.8→1.36.4, then 1.36.4→1.37.0 only for qualified combinations. Existing 1.33 clusters need their own sequential 1.33→1.34→1.35 hops; do not copy an old example version into the live upgrade target.
- [ ] Write recovery procedures for each transaction. Do not promise Kubernetes downgrade or blind containerd data-directory rollback. Restore a rehearsed consistent etcd/PKI/node state or rebuild affected nodes; use provider-specific rollback only when its CRD/storage migration permits it.
- [ ] Commit: `fix: enforce safe phased cluster upgrades and recovery gates`.

### Task 10: Qualify every supported entrypoint and publish the support matrix

**Files:** Create `.github/workflows/validate.yml`, `tests/requirements.txt`, `tests/integration/README.md`, `tests/check_repository.py`; update `meta/runtime.yml`, `galaxy.yml`, `README.md`, role READMEs, `docs/configuration-reference.md`, `docs/getting-started.md`, `docs/production-deployment.md`, `docs/quick-reference.md`, `docs/architecture.md`, `docs/troubleshooting.md`, `playbooks/README.md`, `playbooks/QUICK_REFERENCE.md`, and all deployment examples carrying old versions.

**Interface:** The support matrix records exact OS, architecture, Kubernetes, runtime, CNI, artifact digests, installation method, and test results. CI exercises nonprivileged checks; dedicated disposable VMs run privileged integration tests.

- [ ] Declare actual Ansible collection dependencies and a tested minimum core version. Start qualification with the review environment's core 2.20.7; test a lower floor before advertising it. Replace the untested Ansible 2.9 support claim. Pin test dependencies and use a temporary collection layout.
- [ ] Add CI for YAML parsing, syntax checks, unit/template tests, missing-template references, and mutable artifact references. The missing-template regression must catch Docker and Podman failures found in this review. Do not run the existing localhost role tests on a developer/controller host.
- [ ] Run the following matrix in isolated VMs. Use Ubuntu 24.04 amd64, Debian 13 amd64, and a maintained RPM distribution such as Rocky 9 with qualified binary selection as initial coverage; add arm64 coverage before claiming it. Package availability is a gate, especially for Podman. Record unsupported OS/version tuples explicitly.

| Suite | Required coverage |
| --- | --- |
| Runtime standalone | containerd, CRI-O, Docker, Podman: fresh install, matching rerun, source-version upgrade where supported, restart, persistent data, registry configuration |
| Kubernetes baseline | 1.36.4 × containerd 2.3.5/2.4.0, CRI-O 1.36.6, Docker 29.8.1 + cri-dockerd 0.4.4 × Cilium 1.20.2, Calico 3.32.2, Flannel 0.28.9 |
| Secondary networking | Multus 4.3.1 with each maintained primary CNI and each CRI runtime; real NetworkAttachmentDefinition and secondary-interface traffic |
| Latest qualification | Kubernetes 1.37.0 with each available matching runtime/provider; record unsupported or experimental combinations, never count skipped jobs as passes |
| Upgrade topology | Single-node outage case; primary + worker; three control planes + workers, with node aliases and strict phase ordering |
| Failure/recovery | Drain failure, checksum failure, corrupt backup, unavailable package, CNI rollout failure, NotReady node, interrupted rollout, restored etcd/PKI |
| Existing features | Registry mirrors, ramdisk mode, Gateway HTTP/TLS traffic, Calico policy, custom CIDR/MTU, source builds, offline artifacts |
| Explicit exclusions | Weave latest-stack deployment and Podman-as-CRI fail with actionable messages before mutation |

- [ ] For source-build/offline examples, package all required binaries, checksums, OS packages, keys, images, Helm/manifests, and tools. Test with external egress blocked; merely disabling endpoint checks does not make an install offline. Preserve the source versions of etcd and other bundled components required by kubeadm.
- [ ] Update every stale example. Keep historical hop playbooks clearly labeled with their source and target; active fresh-install examples inherit current defaults. Standalone runtime playbooks use provider-specific version inputs. Document package unavailability and unsupported combinations instead of promising every release on every OS.
- [ ] Publish the matrix and release notes with exact successful combinations and remaining 1.37 qualification limits. Select a collection release version consistent with any changed support/variable contracts; do not automatically describe this as a patch release.
- [ ] Run `python3 -m unittest discover -s tests/unit`, `python3 tests/check_repository.py`, all playbook syntax checks, collection build, and the required VM jobs. Save logs, rendered configs, observed versions, checksums, and recovery evidence.
- [ ] Commit: `test: qualify stack updates and refresh deployment documentation`.

## Deployment sequence after implementation and lab qualification

1. Discover the actual source tuple on every node, including OS/kernel/glibc, package ownership, CRI socket, runtime/CNI versions, CNI values, Gateway stored versions, Multus attachments, and topology. Repository defaults are not evidence of live versions.
2. Select a complete compatibility path. For the default source tuple, patch Cilium 1.19.6→1.19.8; update the current Kubernetes minor to its qualified patch; move runtimes through supported steps and validate each; update Gateway CRDs where enabled and Cilium to 1.20.2 while both source and target Kubernetes minors are supported. Other providers use their own reviewed bridge paths.
3. Take validated off-node cluster and workload backups before disruptive phases. Run the rehearsed provider update once per cluster and runtime updates once per drained node. Confirm pod creation and traffic after each transaction.
4. Upgrade Kubernetes one minor at a time, primary then additional control planes then workers. For CRI-O, coordinate the matching runtime minor within that node's Kubernetes transition rather than changing every runtime minor globally in advance.
5. Hold at the qualified 1.36 baseline where 1.37 support evidence is incomplete. Test and promote the latest profile per provider when upstream release/compatibility evidence and local acceptance are sufficient. Weave moves through replacement-cluster migration; Podman follows a separate standalone maintenance window.
6. Run workload acceptance, external ingress, DNS, persistent storage, CNI policies, and secondary-network checks. Record observed versions and leave failed nodes cordoned until recovered.

## Completion criteria

- Every option has a tested update implementation or an explicit, documented retirement/unsupported path; none disappears silently.
- Supported installs honor exact requested versions and produce healthy services; matching reruns do not repeat disruptive work.
- All three maintained primary CNIs work with the advertised CRI runtimes on recorded qualified tuples; Multus and Gateway integrations pass their own checks.
- Kubernetes 1.37 is promoted only for qualified combinations; holding an unqualified provider at 1.36 is documented remaining support work, not a claim that the all-latest objective was achieved.
- Failure-injection and restore tests demonstrate that the rollout stops safely and recovery works.
- Active examples, dependencies, support claims, and offline/source workflows agree with the tested implementation.

## Inputs needed at execution time

The repository review cannot establish the real cluster inventory, current installed versions, target OS lifecycle policy, required uptime, available test infrastructure, or which applications use CNI-specific features. Collect those facts during the discovery phase before scheduling a live rollout. The implementation plan itself does not require access to production nodes.
