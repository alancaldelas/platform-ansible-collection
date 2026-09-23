# Live uninstall test fixtures

These fixtures were exercised on the disposable Fedora 44 node recorded in the
[live-test report](../../../docs/testing/2026-09-22-cluster-uninstall-fedora44.md).
They are not an automatic runner and must not be pointed at a production node.

`workloads.yml` creates two Kubernetes pods, a Service and an emptyDir marker in
namespace `uninstall-smoke`. Apply it only to the test cluster. Wait for both pods
to be Ready, then verify the client can fetch
`http://web.uninstall-smoke.svc.cluster.local/hostname` and read `/data/proof`.

The report also describes the Podman volume/container, standalone containerd
task and host filesystem markers used during the test. In particular, create
`/srv/uninstall-preserve-test/keep` containing `preserve-test` followed by a
newline. A symlink from `/var/lib/kubelet/uninstall-external-link` to that
sentinel directory tests that cleanup does not traverse the symlink.

Run the uninstall playbook with `--check`, recheck the workloads, then execute
with the explicit confirmation and `k8s_uninstall_reboot=true`.

After reboot, run `verify_fedora_host.py` **as root on the Fedora test node**.
It only reads host state and exits nonzero if targeted resources remain, SSH is
not listening, or the sentinel was not preserved. It requires Python 3, RPM,
`ip` and `ss`. It intentionally uses independent OS observations rather than
calling the uninstall module's own verification function.

Repeat uninstall without reboot to verify a zero-change retry. Remove the
sentinel file and its empty directory afterward. The verification script is
specific to this fixture and Fedora; do not interpret it as a universal audit
of all possible custom container installations.
