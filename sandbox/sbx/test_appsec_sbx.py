"""Host-side regression tests; no sbx daemon required."""
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from appsec_sbx import providers
from appsec_sbx.cli import build_parser, dispatch
from appsec_sbx.credentials import ensure_binding, render_kit
from appsec_sbx.git_source import require_git
from appsec_sbx.lifecycle import (BOOTSTRAP, BOOTSTRAP_ALLOW, Managed, Phases, create_command, lf_bootstrap,
                                  migrate)
from appsec_sbx.policy import DENY, compile_denies, validate_policy
from appsec_sbx import sbxcli
from appsec_sbx.transfer import (guest_home_path, pack_repository, pack_skills, read_lstat, read_nofollow_fd,
                                 read_regular)

OPENROUTER = providers.resolve("openrouter")
ALLOW = providers.allowed(OPENROUTER)


def allow(*resources):
    return {"resource_type": "network", "decision": "allow", "resources": list(resources)}


class ProviderTests(unittest.TestCase):
    def test_presets_are_one_provider_each(self):
        for name in providers.PROVIDERS:
            profile = providers.resolve(name)
            hosts = {e.rsplit(":", 1)[0] for e in profile["endpoints"]}
            # One provider per VM (M2); a provider may need more than one host (claude-code: two).
            self.assertLessEqual(len(hosts), 3, name)  # codex: api, auth, chatgpt
            self.assertTrue(all(providers.ENDPOINT.match(e) for e in profile["endpoints"]), name)
            self.assertEqual(providers.allowed(profile), set(profile["endpoints"]) | {providers.DEFAULT_REGISTRY})
        self.assertEqual(providers.resolve("claude-code")["endpoints"],
                         ["api.anthropic.com:443", "platform.claude.com:443"])

    def test_custom_endpoint_requires_key_var_and_exactness(self):
        with self.assertRaises(providers.ProfileError):
            providers.resolve(endpoint="api.example.com:443")
        for bad in ("*.example.com:443", "example.com", "EXAMPLE.com:443", "example.com:70000", "**"):
            with self.subTest(bad=bad), self.assertRaises(providers.ProfileError):
                providers.resolve(endpoint=bad, key_var="EXAMPLE_API_KEY")
        with self.assertRaises(providers.ProfileError):
            providers.resolve(endpoint="api.example.com:443", key_var="lower")
        profile = providers.resolve(endpoint="api.example.com:443", key_var="EXAMPLE_API_KEY", registry=None)
        self.assertEqual(providers.allowed(profile), {"api.example.com:443"})

    def test_preset_and_custom_are_exclusive(self):
        with self.assertRaises(providers.ProfileError):
            providers.resolve("anthropic", endpoint="x.y:1")
        with self.assertRaises(providers.ProfileError):
            providers.resolve("openrouter", registry="openrouter.ai:443")

    def test_harness_follows_provider(self):
        self.assertEqual(providers.resolve("openrouter")["harness"], "opencode")
        self.assertEqual(providers.resolve("anthropic")["harness"], "opencode")
        self.assertEqual(providers.resolve("claude-code")["harness"], "claude-code")
        self.assertEqual(providers.resolve("codex")["harness"], "codex")
        codex = providers.resolve("codex")
        self.assertEqual(codex["endpoints"], ["api.openai.com:443", "auth.openai.com:443", "chatgpt.com:443"])
        self.assertEqual(codex["key_var"], "OPENAI_API_KEY")
        # A login-only profile (no key variable) is still representable and described as such.
        self.assertIn("harness login", providers.describe({"provider": "x", "endpoints": ["a.b:1"], "key_var": None,
                                                           "registry": [], "harness": "codex"}))
        self.assertEqual(providers.resolve("openrouter", harness="codex")["harness"], "codex")
        self.assertEqual(providers.resolve("openrouter", harness="pi")["harness"], "pi")
        self.assertEqual(providers.resolve("openrouter")["harness"], "opencode")  # pi stays opt-in
        for bad in ("both", "cursor"):
            with self.subTest(bad=bad), self.assertRaises(providers.ProfileError):
                providers.resolve("openrouter", harness=bad)
        legacy_both = {"id": "x", "profile": {"provider": "openrouter", "endpoints": ["a.b:1"], "key_var": "K",
                                              "registry": [], "harness": "both"}}
        self.assertEqual(migrate(legacy_both)["profile"]["harness"], "opencode")
        self.assertEqual(migrate({"id": "x", "profile": {"provider": "openrouter", "endpoints": ["a.b:1"],
                                                          "key_var": "K", "registry": []}})["profile"]["harness"], "opencode")
        self.assertNotIn("harness", migrate({"id": "x", "profile": dict(providers.OFFLINE)})["profile"])

    def test_registry_names_and_lists(self):
        pypi = providers.resolve("openrouter", registry=["pypi", "npm"])
        self.assertEqual(providers.allowed(pypi),
                         {"openrouter.ai:443", "registry.npmjs.org:443", "pypi.org:443", "files.pythonhosted.org:443"})
        self.assertEqual(providers.resolve("openrouter", registry="npm")["registry"], ["registry.npmjs.org:443"])
        self.assertEqual(providers.resolve("openrouter", registry=None)["registry"], [])
        with self.assertRaises(providers.ProfileError):
            providers.resolve("openrouter", registry=["pypi", "*.example.com:443"])
        # v0.1 state stored a single string; allowed() and describe() accept it.
        legacy = {"provider": "openrouter", "endpoints": ["openrouter.ai:443"], "key_var": "X", "registry": "registry.npmjs.org:443"}
        self.assertEqual(providers.allowed(legacy), ALLOW)
        self.assertIn("registry.npmjs.org:443", providers.describe(legacy))


class PolicyTests(unittest.TestCase):
    def test_balanced_grants_are_subtracted(self):
        denies = compile_denies([allow("registry.npmjs.org:443", "**.github.com:443", "nodejs.org:443")], ALLOW)
        self.assertEqual(denies, DENY | {"**.github.com:443", "nodejs.org:443"})
        self.assertTrue(denies.isdisjoint(ALLOW))

    def test_broad_overlapping_grants_fail_closed(self):
        for grant in ("**", "*", "**:443", "*.ai:443", "openrouter.ai", "registry.npmjs.org"):
            with self.subTest(grant=grant), self.assertRaises(RuntimeError):
                compile_denies([allow(grant)], ALLOW)

    def test_anthropic_profile_denies_openrouter(self):
        anthropic = providers.allowed(providers.resolve("anthropic"))
        denies = compile_denies([allow("openrouter.ai:443", "api.anthropic.com:443")], anthropic)
        self.assertIn("openrouter.ai:443", denies)
        self.assertNotIn("api.anthropic.com:443", denies)

    def test_deny_does_not_become_allow(self):
        self.assertEqual(compile_denies([dict(allow("openrouter.ai:443"), decision="deny")], ALLOW), DENY)

    def test_late_inherited_grant_is_rejected(self):
        rules = [dict(allow(*ALLOW), scope="sandbox:test"),
                 dict(allow(*DENY), scope="sandbox:test", decision="deny"),
                 dict(allow("new-grant.example:443"), scope="global")]
        with self.assertRaises(RuntimeError):
            validate_policy(rules, "test", ALLOW)

    def test_offline_requires_wildcard_deny(self):
        rules = [dict(allow(*DENY), scope="sandbox:r", decision="deny")]
        with self.assertRaises(RuntimeError):
            validate_policy(rules, "r", set())
        rules.append(dict(allow("**"), scope="sandbox:r", decision="deny"))
        validate_policy(rules, "r", set())


class SbxContractTests(unittest.TestCase):
    """The wrapper's own sbx calls must never wait on a prompt (threat model M25)."""

    def test_lock_policy_removes_rules_with_force(self):
        # sbx 0.45.0 (checked 2026-09-22): `policy rm` asks for confirmation and, without a
        # terminal, fails with "stdin is not a terminal; use --force to skip confirmation".
        kit_grant = {"id": "kit1", "scope": "sandbox:lockme", "resource_type": "network",
                     "decision": "allow", "resources": ["github.com:443"], "editable": True}
        calls = []

        def recording_sbx(*args, **kwargs):
            calls.append(args)
            if args[:2] == ("policy", "check"):
                verdict = {"allowed": args[5] in ALLOW, "governance": {"active": False}}
                return mock.Mock(stdout=json.dumps(verdict).encode())
            return mock.Mock(stdout=b"")

        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary}):
            vm = Managed("lockme")
            vm.data["profile"] = OPENROUTER
            with mock.patch("appsec_sbx.lifecycle.policy", return_value=[kit_grant]), \
                    mock.patch("appsec_sbx.lifecycle.sbx", side_effect=recording_sbx), \
                    mock.patch("appsec_sbx.lifecycle.validate_policy"):
                vm.lock_policy()
        removals = [call for call in calls if call[:2] == ("policy", "rm")]
        self.assertEqual(removals, [
            ("policy", "rm", "network", "--sandbox", "lockme", "--id", "kit1", "--force"),
            ("policy", "rm", "network", "--sandbox", "lockme", "--resource", "**", "--force")])
        self.assertTrue(all("--force" in call for call in calls if call[:1] == ("rm",)))

    def test_create_command_uses_explicit_tri_state_skills_flag(self):
        fresh = create_command("pilot", "/state/pilot/kit")
        self.assertEqual(fresh[:3], ["create", "/state/pilot/kit", "--name"])
        self.assertIn("--skills", fresh)
        self.assertEqual(fresh[fresh.index("--skills") + 1], "off")
        self.assertNotIn("--no-share-skills", fresh)
        denied = {fresh[i + 1] for i, arg in enumerate(fresh) if arg == "--deny-network"}
        self.assertEqual(denied, DENY)
        from_template = create_command("pilot", "/state/pilot/kit", "appsec-clean:t")
        denied = {from_template[i + 1] for i, arg in enumerate(from_template) if arg == "--deny-network"}
        self.assertEqual(denied, DENY | {"**"})
        self.assertEqual(from_template[-2:], ["--template", "appsec-clean:t"])

    def completed(self, stdout, returncode=0):
        return subprocess.CompletedProcess(["sbx", "version"], returncode, stdout=stdout, stderr=b"")

    def test_preflight_requires_the_checked_sbx_release(self):
        with mock.patch.object(sbxcli, "run", return_value=self.completed(b"sbx version: v0.42.1 cc6e400a\n")), \
                mock.patch.object(sbxcli, "js") as js, \
                self.assertRaisesRegex(RuntimeError, r"v0\.45\.0 or newer is required \(found v0\.42\.1\)"):
            sbxcli.preflight()
        js.assert_not_called()
        with mock.patch.object(sbxcli, "run", return_value=self.completed(b"sbx version: v0.45.0 2f44e051\n")), \
                mock.patch.object(sbxcli, "js", side_effect=[{"value": False}, {"servers": []}]):
            sbxcli.preflight()
        for stdout, code in ((b"", 0), (b"sbx: command not found\n", 127)):
            with mock.patch.object(sbxcli, "run", return_value=self.completed(stdout, code)), \
                    self.assertRaisesRegex(RuntimeError, "Cannot read the sbx release"):
                sbxcli.sbx_version()


class GitPreflightTests(unittest.TestCase):
    def test_accepts_platform_version_strings(self):
        for output in (b"git version 2.51.0\n", b"git version 2.51.0.windows.1\r\n",
                       b"git version 2.50.1 (Apple Git-155)\n"):
            with self.subTest(output=output), mock.patch("subprocess.run", return_value=
                    subprocess.CompletedProcess(["git"], 0, stdout=output)) as run:
                require_git()
                self.assertEqual(run.call_args.kwargs["timeout"], 10)
                self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_missing_broken_or_hung_git_has_actionable_error(self):
        for error in (FileNotFoundError("git not found"), PermissionError("not executable"),
                      subprocess.CalledProcessError(1, ["git", "--version"]),
                      subprocess.TimeoutExpired(["git", "--version"], 10)):
            with self.subTest(error=type(error).__name__), mock.patch("subprocess.run", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, "System Git") as raised:
                    require_git()
                self.assertIn("PATH", str(raised.exception))
                self.assertIn("git --version", str(raised.exception))

    def test_successful_non_git_executable_is_rejected(self):
        for output in (b"", b"hello\n", b"git version broken\n"):
            with self.subTest(output=output), mock.patch("subprocess.run", return_value=
                    subprocess.CompletedProcess(["git"], 0, stdout=output)):
                with self.assertRaisesRegex(RuntimeError, "unexpected version"):
                    require_git()

    def test_failure_precedes_vm_access_for_local_and_remote_sources(self):
        for action in ("import", "skills"):
            for source in ("local-checkout", "https://github.com/example/repo"):
                with self.subTest(action=action, source=source), \
                        mock.patch("appsec_sbx.cli.require_git", side_effect=RuntimeError("missing Git")), \
                        mock.patch("appsec_sbx.cli.Managed") as managed:
                    args = build_parser().parse_args([action, "test-vm", source])
                    with self.assertRaisesRegex(RuntimeError, "missing Git"):
                        dispatch(args)
                    managed.assert_not_called()

    def test_stop_does_not_depend_on_git(self):
        with mock.patch("appsec_sbx.cli.require_git", side_effect=RuntimeError("missing Git")) as check, \
                mock.patch("appsec_sbx.cli.Managed") as managed:
            dispatch(build_parser().parse_args(["stop", "test-vm"]))
            check.assert_not_called()
            managed.return_value.stop.assert_called_once_with()


class SbxJsonTests(unittest.TestCase):
    def completed(self, stdout=b"", stderr=b"", returncode=0):
        return subprocess.CompletedProcess(["sbx"], returncode, stdout=stdout, stderr=stderr)

    def test_parses_json_and_passes_stderr_through(self):
        with mock.patch.object(sbxcli, "run", return_value=self.completed(b'{"rules": []}', b"warn\n")) as run, \
                mock.patch("sys.stderr") as stderr:
            self.assertEqual(sbxcli.js("policy", "ls"), {"rules": []})
        self.assertEqual(run.call_args.args[0], ["sbx", "policy", "ls", "--json"])
        stderr.buffer.write.assert_called_once_with(b"warn\n")

    def test_empty_or_non_json_output_names_the_command(self):
        # The first Linux attempt (2026-09-11): exit 0, empty stdout, bare JSONDecodeError.
        for stdout, code in ((b"", 0), (b"POLICY  SOURCE\n", 0), (b"", 1)):
            with mock.patch.object(sbxcli, "run", return_value=self.completed(stdout, returncode=code)), \
                    self.assertRaises(RuntimeError) as raised:
                sbxcli.js("policy", "ls")
            message = str(raised.exception)
            self.assertIn("sbx policy ls --json", message)
            self.assertIn(f"exited {code}", message)
            self.assertIn("<empty>" if not stdout else "POLICY", message)


class PhasesTests(unittest.TestCase):
    def test_laps_are_ordered_and_reported(self):
        clock = iter([100.0, 101.5, 130.25])
        with mock.patch("appsec_sbx.lifecycle.time.monotonic", side_effect=lambda: next(clock)):
            phases = Phases()
            phases.lap("sbx create")
            phases.lap("bootstrap")
        self.assertEqual(list(phases.durations.items()), [("sbx create", 1.5), ("bootstrap", 28.8)])
        with mock.patch("builtins.print") as printed:
            phases.report()
            Phases().report()
        printed.assert_called_once_with("Phases: sbx create 2s, bootstrap 29s")


class BootstrapTests(unittest.TestCase):
    def test_provisioning_grants_are_tls_only(self):
        # M24: the bootstrap's Ubuntu mirror rewrite makes :80 grants unnecessary; keep them out.
        self.assertTrue(all(e.endswith(":443") for e in BOOTSTRAP_ALLOW), sorted(BOOTSTRAP_ALLOW))
        self.assertLessEqual({"archive.ubuntu.com:443", "security.ubuntu.com:443", "ports.ubuntu.com:443"}, BOOTSTRAP_ALLOW)

    def test_bootstrap_is_staged_with_lf_endings(self):
        # Windows create, 2026-09-14: a core.autocrlf checkout copied CRLF into the guest and
        # bash stopped at `set -euo pipefail\r`. The guest must only ever see the staged copy.
        self.assertNotIn(b"\r", Path(BOOTSTRAP).read_bytes(), ".gitattributes pins LF for guest files")
        crlf = b"#!/usr/bin/env bash\r\nset -euo pipefail\r\necho ok\r\n"
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "bootstrap.sh"
            source.write_bytes(crlf)
            with mock.patch("appsec_sbx.lifecycle.BOOTSTRAP", source), lf_bootstrap() as staged:
                self.assertNotEqual(staged, source)
                self.assertEqual(staged.read_bytes(), crlf.replace(b"\r\n", b"\n"))
            self.assertFalse(staged.exists())
            self.assertEqual(source.read_bytes(), crlf)

    def test_mirror_rewrite_precedes_the_first_apt_update(self):
        lines = Path(BOOTSTRAP).read_text().splitlines()
        rewrite = next(i for i, l in enumerate(lines) if "https://\\1.ubuntu.com/" in l)
        guard = next(i for i, l in enumerate(lines) if "plain-HTTP Ubuntu mirror" in l)
        update = next(i for i, l in enumerate(lines) if l.startswith("apt-get update"))
        self.assertLess(rewrite, guard)
        self.assertLess(guard, update)

    def test_mirror_rewrite_handles_deb822_and_legacy_sources(self):
        script = Path(BOOTSTRAP).read_text()
        sed = next(l.strip() for l in script.splitlines() if "sed -i -E" in l)
        expression = sed.split("sed -i -E ")[1].split(" \"$f\"")[0].strip("'")
        deb822 = ("Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/ http://security.ubuntu.com/ubuntu/\nSuites: resolute\n")
        legacy = ("deb http://ports.ubuntu.com/ubuntu-ports/ resolute main\n"
                  "deb https://download.docker.com/linux/ubuntu resolute stable\n")
        out = [subprocess.run(["sed", "-E", expression], input=text.encode(), stdout=subprocess.PIPE, check=True)
               .stdout.decode() for text in (deb822, legacy)]
        self.assertEqual(out[0].splitlines()[1], "URIs: https://archive.ubuntu.com/ubuntu/ https://security.ubuntu.com/ubuntu/")
        self.assertEqual(out[1].splitlines(), ["deb https://ports.ubuntu.com/ubuntu-ports/ resolute main",
                                               "deb https://download.docker.com/linux/ubuntu resolute stable"])


class StateTests(unittest.TestCase):
    def test_v01_state_migrates_to_profiles(self):
        self.assertEqual(migrate({"id": "x", "offline": False})["profile"], OPENROUTER)
        self.assertEqual(migrate({"id": "x", "offline": True})["profile"], providers.OFFLINE)
        self.assertNotIn("offline", migrate({"id": "x", "offline": True}))
        self.assertEqual(migrate({}), {})

    def test_managed_persists_migration(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary}):
            directory = Path(temporary) / "legacy"
            directory.mkdir()
            (directory / "state.json").write_text(json.dumps({"id": "abc", "ready": True, "offline": False}))
            vm = Managed("legacy")
            self.assertEqual(vm.allowed, ALLOW)
            self.assertEqual(json.loads((directory / "state.json").read_text())["profile"], OPENROUTER)
            with self.assertRaises(RuntimeError):
                Managed("Bad_Name")

    def test_reset_restores_ready_when_rm_fails_without_removing_the_vm(self):
        # Windows over SSH, 2026-09-14: `sbx rm --force` failed on the Credential Manager and the
        # primary was left at ready=False with the VM intact, refusing every action.
        vm_record = {"id": "abc", "workspaces": []}
        def failing_sbx(*args, **kwargs):
            if args[:1] == ("rm",):
                raise subprocess.CalledProcessError(1, ["sbx", *args])
            return mock.Mock(stdout=b"")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary}):
            vm = Managed("resetme")
            vm.data.update({"id": "abc", "ready": True, "profile": OPENROUTER, "template": "appsec-clean:t"})
            vm.save()
            with mock.patch("appsec_sbx.lifecycle.preflight"), mock.patch("appsec_sbx.lifecycle.policy", return_value=[]), \
                    mock.patch("appsec_sbx.lifecycle.compile_denies", return_value=set()), \
                    mock.patch("appsec_sbx.lifecycle.sbx", side_effect=failing_sbx), \
                    mock.patch.object(Managed, "lookup", return_value=vm_record), \
                    mock.patch.object(Managed, "create") as create:
                with self.assertRaisesRegex(RuntimeError, "nothing was reset"):
                    vm.reset()
                create.assert_not_called()
            self.assertTrue(json.loads(Path(vm.path).read_text())["ready"])
            # The VM really gone despite the error: stay down and surface sbx's own failure.
            with mock.patch("appsec_sbx.lifecycle.preflight"), mock.patch("appsec_sbx.lifecycle.policy", return_value=[]), \
                    mock.patch("appsec_sbx.lifecycle.compile_denies", return_value=set()), \
                    mock.patch("appsec_sbx.lifecycle.sbx", side_effect=failing_sbx), \
                    mock.patch.object(Managed, "lookup", side_effect=[vm_record, None]), \
                    mock.patch.object(Managed, "create") as create:
                with self.assertRaises(subprocess.CalledProcessError):
                    vm.reset()
            self.assertFalse(json.loads(Path(vm.path).read_text())["ready"])

    def test_credential_hint_speaks_only_when_nothing_is_stored_or_logged_in(self):
        credential = providers.credential(OPENROUTER)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary}):
            vm = Managed("hint")
            vm.data.update({"profile": OPENROUTER, "credential": credential})
            # The stored key is checked on the host; only when absent is the guest asked for login stores.
            with mock.patch("appsec_sbx.lifecycle.js", return_value={"secrets": [{"name": credential["service"]}]}) as ls, \
                    mock.patch("appsec_sbx.lifecycle.guest") as probe, mock.patch("sys.stderr") as stderr:
                vm.credential_hint()
                self.assertEqual(ls.call_args.args, ("secret", "ls", "--sandbox", "hint"))
                probe.assert_not_called()
                self.assertFalse(stderr.write.called)
            for code, spoken in ((1, True), (0, False)):
                with mock.patch("appsec_sbx.lifecycle.js", return_value={"secrets": []}), \
                        mock.patch("appsec_sbx.lifecycle.guest", return_value=mock.Mock(returncode=code)) as probe, \
                        mock.patch("sys.stderr") as stderr:
                    vm.credential_hint()
                    self.assertEqual(probe.call_count, 1)
                    self.assertNotIn("/run/appsec/env", probe.call_args.args)
                    self.assertIn("/home/appsec/.codex/auth.json", probe.call_args.args)
                    self.assertEqual(stderr.write.called, spoken, code)
            vm.data["profile"] = providers.OFFLINE
            with mock.patch("appsec_sbx.lifecycle.js") as ls, mock.patch("appsec_sbx.lifecycle.guest") as probe:
                vm.credential_hint()
                ls.assert_not_called()
                probe.assert_not_called()


class ManagedCredentialTests(unittest.TestCase):
    """The key never enters the guest (threat model M17): sbx stores it per VM and its proxy injects it."""

    def test_presets_declare_one_proxy_managed_credential(self):
        openrouter = providers.credential(OPENROUTER)
        self.assertEqual(openrouter, {"service": "appsec-openrouter", "variable": "OPENROUTER_API_KEY",
                                      "inject": [{"domain": "openrouter.ai", "header": "Authorization",
                                                  "format": "Bearer %s"}]})
        anthropic = providers.credential(providers.resolve("anthropic"))
        self.assertEqual(anthropic["inject"], [{"domain": "api.anthropic.com", "header": "x-api-key", "format": "%s"}])
        # Seat and login hosts never receive the stored value: only the API host is bound.
        self.assertEqual([e["domain"] for e in providers.credential(providers.resolve("claude-code"))["inject"]],
                         ["api.anthropic.com"])
        self.assertEqual([e["domain"] for e in providers.credential(providers.resolve("codex"))["inject"]],
                         ["api.openai.com"])
        custom = providers.credential(providers.resolve(endpoint="api.example.com:443", key_var="EXAMPLE_API_KEY"))
        self.assertEqual(custom["service"], "appsec-custom-api-example-com-443")
        self.assertTrue(providers.SERVICE.match(custom["service"]))
        self.assertEqual(custom["inject"][0]["domain"], "api.example.com")
        self.assertIsNone(providers.credential(providers.OFFLINE))
        for name in providers.PROVIDERS:
            self.assertTrue(providers.SERVICE.match(providers.credential(providers.resolve(name))["service"]), name)

    def test_kit_declares_the_credential_or_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            spec = (render_kit(Path(temporary) / "kit", providers.credential(OPENROUTER)) / "spec.yaml").read_text()
            self.assertIn('schemaVersion: "2"', spec)
            self.assertIn("image: docker/sandbox-templates:shell-docker", spec)
            self.assertIn("  - service: appsec-openrouter", spec)
            self.assertIn("      name: OPENROUTER_API_KEY", spec)
            self.assertIn("      proxyManaged: true", spec)
            self.assertIn('        - domain: "openrouter.ai"', spec)
            self.assertIn('          format: "Bearer %s"', spec)
            self.assertNotIn("\r", spec)
            offline = (render_kit(Path(temporary) / "repro", None) / "spec.yaml").read_text()
            self.assertNotIn("credentials", offline)
            self.assertNotIn("proxyManaged", offline)

    def test_binding_file_is_created_merged_or_refused(self):
        credential = providers.credential(OPENROUTER)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sbx" / "credentials.yaml"
            self.assertEqual(ensure_binding(credential, path), "written")
            self.assertEqual(path.read_text(), "bindings:\n  appsec-openrouter:\n    apiKey:\n      domains: [openrouter.ai]\n")
            self.assertEqual(ensure_binding(credential, path), "present")
            # An operator's own bindings stay; ours is inserted under the existing key with its indentation.
            path.write_text("# mine\nbindings:\n    github:\n        apiKey:\n            domains: [api.github.com, github.com]\n")
            self.assertEqual(ensure_binding(credential, path), "added")
            text = path.read_text()
            self.assertIn("    github:\n", text)
            self.assertIn("bindings:\n    appsec-openrouter:\n      apiKey:\n        domains: [openrouter.ai]\n    github:", text)
            self.assertEqual(ensure_binding(credential, path), "present")
            # A block-style domain list of ours is recognised; a conflicting binding is refused, not rewritten.
            path.write_text("bindings:\n  appsec-openrouter:\n    apiKey:\n      domains:\n        - openrouter.ai\n")
            self.assertEqual(ensure_binding(credential, path), "present")
            path.write_text("bindings:\n  appsec-openrouter:\n    apiKey:\n      domains: [evil.example]\n")
            with self.assertRaisesRegex(RuntimeError, "already binds appsec-openrouter"):
                ensure_binding(credential, path)
            # No bindings key at all: appended.
            path.write_text("other: 1\n")
            self.assertEqual(ensure_binding(credential, path), "added")
            self.assertTrue(path.read_text().endswith("other: 1\nbindings:\n  appsec-openrouter:\n    apiKey:\n      domains: [openrouter.ai]\n"))

    def managed(self, temporary, credential):
        vm = Managed("keyed")
        vm.data.update({"id": "abc", "ready": True, "profile": OPENROUTER, "credential": credential,
                        "template": "appsec-clean:t"})
        vm.save()
        return vm

    def test_key_is_stored_sandbox_scoped_on_stdin_and_never_in_the_guest(self):
        credential = providers.credential(OPENROUTER)
        calls = []
        def recording_sbx(*args, **kwargs):
            calls.append((args, kwargs))
            return mock.Mock(stdout=b"")
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary, "OPENROUTER_API_KEY": "sk-or-test"}):
            vm = self.managed(temporary, credential)
            # First `key`: nothing stored before, the new secret listed afterwards.
            with mock.patch("appsec_sbx.lifecycle.sbx", side_effect=recording_sbx), \
                    mock.patch("appsec_sbx.lifecycle.ensure_binding") as binding, \
                    mock.patch("appsec_sbx.lifecycle.guest") as guest, \
                    mock.patch("appsec_sbx.lifecycle.js", side_effect=[{"secrets": []}, {"secrets": [{"name": "appsec-openrouter"}]}]), \
                    mock.patch("builtins.print"):
                vm.place_key()
            binding.assert_called_once_with(credential)
            guest.assert_not_called()
            self.assertEqual(calls, [(("secret", "set", "appsec-openrouter", "--sandbox", "keyed"), {"input": b"sk-or-test"})])
            # Rotation: sbx prompts before overwriting and cancels without a terminal, so the old
            # value is removed first (prompt-free, M25) and the new one stored.
            calls.clear()
            with mock.patch("appsec_sbx.lifecycle.sbx", side_effect=recording_sbx), \
                    mock.patch("appsec_sbx.lifecycle.ensure_binding"), \
                    mock.patch("appsec_sbx.lifecycle.js", return_value={"secrets": [{"name": "appsec-openrouter"}]}), \
                    mock.patch("builtins.print"):
                vm.place_key()
            self.assertEqual([c[0] for c in calls], [("secret", "rm", "appsec-openrouter", "--sandbox", "keyed", "-f"),
                                                     ("secret", "set", "appsec-openrouter", "--sandbox", "keyed")])
            # The value is never an argument of any sbx call (process listings, shell history).
            self.assertTrue(all("sk-or-test" not in " ".join(map(str, args)) for args, _ in calls))
            # sbx answering without a stored secret is an error, not silence.
            with mock.patch("appsec_sbx.lifecycle.sbx", side_effect=recording_sbx), \
                    mock.patch("appsec_sbx.lifecycle.ensure_binding"), \
                    mock.patch("appsec_sbx.lifecycle.js", side_effect=[{"secrets": []}, {"secrets": []}]), \
                    self.assertRaisesRegex(RuntimeError, "did not record"):
                vm.place_key()
            # VMs created before 0.4.0 have no kit credential and would never see the key.
            vm.data["credential"] = None
            with mock.patch("appsec_sbx.lifecycle.sbx") as sbx_call, \
                    self.assertRaisesRegex(RuntimeError, "created before proxy-managed credentials"):
                vm.place_key()
            sbx_call.assert_not_called()

    def test_stop_and_unkey_remove_the_stored_key_even_when_the_vm_is_stopped(self):
        credential = providers.credential(OPENROUTER)
        for status, guest_cleanup in (("stopped", False), ("running", True)):
            calls = []
            def recording_sbx(*args, **kwargs):
                calls.append(args)
                return mock.Mock(stdout=b"")
            with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary}):
                vm = self.managed(temporary, credential)
                with mock.patch("appsec_sbx.lifecycle.sbx", side_effect=recording_sbx), \
                        mock.patch("appsec_sbx.lifecycle.guest") as guest, \
                        mock.patch.object(Managed, "owned", return_value={"id": "abc", "status": status}):
                    vm.stop()
            self.assertIn(("secret", "rm", "appsec-openrouter", "--sandbox", "keyed", "-f"), calls, status)
            self.assertEqual(calls[-1], ("stop", "keyed"))
            removed_in_guest = any("/home/appsec/.codex/auth.json" in call.args for call in guest.call_args_list)
            self.assertEqual(removed_in_guest, guest_cleanup, status)
            self.assertLess(calls.index(("secret", "rm", "appsec-openrouter", "--sandbox", "keyed", "-f")),
                            calls.index(("stop", "keyed")))

    def test_entry_sets_the_key_variable_only_while_a_key_is_stored(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary}):
            vm = self.managed(temporary, providers.credential(OPENROUTER))
            plain = vm.entry_command("shell")
            keyed = vm.entry_command("shell", keyed=True)
            self.assertNotIn("APPSEC_KEYED=1", plain)
            self.assertEqual(keyed[keyed.index("--") + 1:keyed.index("--") + 4],
                             ["env", "APPSEC_KEYED=1", "/usr/local/libexec/appsec-enter"])
            self.assertEqual(vm.entry_command("exec", ["true"], keyed=True)[-4:],
                             ["-c", 'exec "$@"', "appsec", "true"])
            self.assertNotIn("APPSEC_KEYED=1", vm.entry_command("admin"))
            # The guest profile sources the sentinel file only on that flag, then drops the flag.
            bootstrap = BOOTSTRAP.read_text()
            self.assertIn('[ -z "${APPSEC_KEYED:-}" ] || . /etc/appsec/credential.env', bootstrap)
            self.assertIn("unset APPSEC_KEYED", bootstrap)
            self.assertIn("${APPSEC_KEYED:+APPSEC_KEYED=1}", bootstrap)

    def test_entry_guard_admits_only_the_gateway_and_this_vms_service(self):
        with mock.patch.object(sbxcli, "js", side_effect=[
                {"secrets": [{"name": "mcpgateway"}, {"name": "appsec-openrouter"}]}, []]), \
                mock.patch.object(sbxcli, "guest", return_value=mock.Mock(stdout=b"")):
            sbxcli.isolation("keyed", ("mcpgateway", "appsec-openrouter"))
        with mock.patch.object(sbxcli, "js", side_effect=[
                {"secrets": [{"name": "mcpgateway"}, {"name": "openrouter"}]}, []]), \
                mock.patch.object(sbxcli, "guest"), \
                self.assertRaisesRegex(RuntimeError, "Unexpected sbx credential binding"):
            sbxcli.isolation("keyed", ("mcpgateway", "appsec-openrouter"))


class CliTests(unittest.TestCase):
    def test_create_options(self):
        parser = build_parser()
        args = parser.parse_args(["create", "pilot", "--provider", "anthropic", "--no-registry"])
        self.assertEqual(parser.parse_args(["create", "--registry", "pypi", "--registry", "npm"]).registry, ["pypi", "npm"])
        self.assertEqual(parser.parse_args(["create", "--harness", "codex"]).harness, "codex")
        self.assertEqual(parser.parse_args(["create", "--harness", "pi"]).harness, "pi")
        with self.assertRaises(SystemExit):
            parser.parse_args(["create", "--harness", "both"])
        self.assertEqual((args.name, args.provider, args.no_registry), ("pilot", "anthropic", True))
        args = parser.parse_args(["exec", "vm", "--", "timeout", "60", "true"])
        self.assertEqual(args.command[-3:], ["timeout", "60", "true"])
        self.assertEqual(parser.parse_args(["shell"]).name, "appsec-sbx")
        args = parser.parse_args(["skills", "vm", "/tmp/mantis", "--replace"])
        self.assertEqual((args.name, args.source, args.replace), ("vm", "/tmp/mantis", True))
        self.assertTrue(parser.parse_args(["shell", "--key"]).key)
        self.assertFalse(parser.parse_args(["shell"]).key)
        args = parser.parse_args(["exec", "--key", "vm", "--", "true"])  # before the name: REMAINDER
        self.assertEqual((args.key, args.command), (True, ["true"]))
        self.assertFalse(hasattr(parser.parse_args(["admin"]), "key"))
        with self.assertRaises(SystemExit):
            parser.parse_args(["create", "--provider", "anthropic", "--endpoint", "a.b:1"])

    def test_every_action_has_help_and_description(self):
        from appsec_sbx.cli import ACTIONS
        parser = build_parser()
        subparsers = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(subparsers), set(ACTIONS))
        for name, sub in subparsers.items():
            self.assertTrue(sub.description and sub.description.endswith("."), name)
            for action in sub._actions:
                self.assertTrue(action.help, f"{name} {action.dest} has no help")

    def test_command_reference_page_matches_cli_help(self):
        import gen_command_reference as gen
        if not gen.PAGE.exists():
            self.skipTest("documentation page not present (installed package)")
        self.assertEqual(gen.PAGE.read_text(), gen.render(),
                         "regenerate: python3 sandbox/sbx/gen_command_reference.py > " + str(gen.PAGE))


class PutPathTests(unittest.TestCase):
    def test_destination_must_be_a_file_under_the_workload_home(self):
        self.assertEqual(guest_home_path("/home/appsec/.config/opencode/command/security-review.md"),
                         "/home/appsec/.config/opencode/command/security-review.md")
        for bad in ("/home/appsec/", "/home/appsec/../agent/x", "/run/appsec/env", "/etc/appsec/opencode.json",
                    "relative.md", "/home/appsec/dir/", "/home/appsecX/file", "/home/appsec/a\\b"):
            with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                guest_home_path(bad)


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.archive = Path(self.temporary.name) / "source.tar.gz"

    def add(self, name, content, executable=False):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(0o755)
        subprocess.run(["git", "-C", self.root, "add", "--", name], check=True)

    def test_working_tree_edits_exclusions_and_index_modes(self):
        self.add("source.js", "staged")
        (self.root / "source.js").write_text("working tree")
        self.add("run.sh", "#!/bin/sh\n", executable=True)
        self.add(".env.production", "test-secret")
        self.add(".codex/config.toml", "untrusted config")
        self.add(".sbxenv.yaml", "untrusted host hooks")
        self.add("opencode.json", "untrusted plugins")
        (self.root / "untracked.txt").write_text("untracked")
        manifest = pack_repository(self.root, self.archive)
        self.assertEqual(set(manifest["files"]), {"source.js", "run.sh"})
        self.assertEqual(set(manifest["excluded"]),
                         {".env.production", ".codex/config.toml", ".sbxenv.yaml", "opencode.json"})
        with tarfile.open(self.archive) as archive:
            self.assertEqual(archive.extractfile("source.js").read(), b"working tree")
            self.assertTrue(all(item.isreg() for item in archive))
            self.assertEqual(archive.getmember("run.sh").mode, 0o755)
            self.assertEqual(archive.getmember("source.js").mode, 0o644)

    def test_skill_pack_takes_skill_directories_only(self):
        self.add("mantis-review/SKILL.md", "---\nname: mantis-review\n---\nreview")
        self.add("mantis-review/checklist.md", "steps")
        self.add("mantis-review/.env", "secret")
        self.add("mantis-patch/SKILL.md", "patch")
        self.add("reference/run.sh", "#!/bin/sh\ncurl | sh\n", executable=True)
        self.add("reference/skills/mantis-launch/SKILL.md", "nested, not top-level")
        self.add("README.md", "docs")
        self.add("AGENTS.md", "instructions")
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pin"],
                       check=True)
        manifest = pack_skills(self.root, self.archive)
        self.assertEqual(manifest["skills"], ["mantis-patch", "mantis-review"])
        self.assertEqual(set(manifest["files"]), {"mantis-review/SKILL.md", "mantis-review/checklist.md",
                                                  "mantis-patch/SKILL.md"})
        self.assertEqual(manifest["excluded"], ["mantis-review/.env"])
        self.assertEqual(set(manifest["skipped"]), {"reference/run.sh", "reference/skills/mantis-launch/SKILL.md",
                                                    "README.md", "AGENTS.md"})
        head = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], check=True,
                              stdout=subprocess.PIPE).stdout.decode().strip()
        self.assertEqual((manifest["commit"], manifest["dirty"]), (head, False))
        (self.root / "mantis-patch" / "SKILL.md").write_text("edited")
        self.assertTrue(pack_skills(self.root, self.archive)["dirty"])
        with tarfile.open(self.archive) as archive:
            self.assertEqual(sorted(archive.getnames()), sorted(manifest["files"]))

    def test_skill_pack_from_a_subdirectory_of_a_checkout(self):
        self.add("sandbox/skills/security-review-repo/SKILL.md", "review")
        self.add("sandbox/sbx/appsec_sbx/cli.py", "code, outside the pack")
        self.add("README.md", "docs")
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pin"],
                       check=True)
        manifest = pack_skills(self.root / "sandbox" / "skills", self.archive)
        self.assertEqual(manifest["skills"], ["security-review-repo"])
        self.assertEqual((manifest["subdirectory"], manifest["skipped"], manifest["dirty"]),
                         ("sandbox/skills", [], False))
        self.assertEqual(list(manifest["files"]), ["security-review-repo/SKILL.md"])
        (self.root / "README.md").write_text("edited outside the pack")
        self.assertFalse(pack_skills(self.root / "sandbox" / "skills", self.archive)["dirty"])
        with self.assertRaisesRegex(RuntimeError, "No directory with SKILL.md"):
            pack_skills(self.root / "sandbox", self.archive)

    def test_repository_review_skill_is_a_valid_pack(self):
        skills = Path(__file__).resolve().parent.parent / "skills"
        manifest = pack_skills(skills, self.archive)
        self.assertIn("security-review-repo", manifest["skills"])
        text = (skills / "security-review-repo" / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: security-review-repo\ndescription: "))
        for needed in ("allowed-tools:", "$ARGUMENTS", "FALSE POSITIVE FILTERING", "/home/appsec/out/findings.md"):
            self.assertIn(needed, text)
        self.assertNotIn("!`", text)

    def test_skill_pack_refuses_odd_names_and_empty_packs(self):
        self.add("README.md", "no skills here")
        with self.assertRaisesRegex(RuntimeError, "no commit"):
            pack_skills(self.root, self.archive)
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pin"],
                       check=True)
        with self.assertRaisesRegex(RuntimeError, "No directory with SKILL.md"):
            pack_skills(self.root, self.archive)
        self.add("Bad_Name/SKILL.md", "underscore and capitals")
        with self.assertRaises(RuntimeError):
            pack_skills(self.root, self.archive)

    def test_symlink_index_entry_is_rejected_by_name(self):
        self.add("file", "data")
        (self.root / "link").symlink_to("file")
        subprocess.run(["git", "-C", self.root, "add", "link"], check=True)
        with self.assertRaisesRegex(RuntimeError, "Symlink in the Git index"):
            pack_repository(self.root, self.archive)

    def test_submodule_is_rejected_by_name(self):
        self.add("file", "data")
        sub = Path(self.temporary.name) / "sub"
        sub.mkdir()
        subprocess.run(["git", "init", "-q", sub], check=True)
        (sub / "x").write_text("x")
        subprocess.run(["git", "-C", sub, "-c", "user.email=t@t", "-c", "user.name=t", "add", "x"], check=True)
        subprocess.run(["git", "-C", sub, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x"], check=True)
        subprocess.run(["git", "-C", self.root, "-c", "protocol.file.allow=always", "submodule", "add", "-q",
                        str(sub), "vendor"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with self.assertRaisesRegex(RuntimeError, "Submodule"):
            pack_repository(self.root, self.archive)

    def test_hardlink_is_rejected(self):
        self.add("file", "data")
        os.link(self.root / "file", self.root / "hardlink")
        with self.assertRaises(RuntimeError):
            pack_repository(self.root, self.archive)

    def test_symlink_parent_is_rejected_by_both_readers(self):
        self.add("dir/file", "data")
        (self.root / "dir").rename(self.root / "real")
        (self.root / "dir").symlink_to("real", target_is_directory=True)
        with self.assertRaises(OSError):
            read_nofollow_fd(self.root, "dir/file")
        with self.assertRaises(RuntimeError):
            read_lstat(self.root, "dir/file")
        with self.assertRaises((OSError, RuntimeError)):
            pack_repository(self.root, self.archive)

    def test_traversal_and_fifo_are_rejected_by_both_readers(self):
        os.mkfifo(self.root / "fifo")
        for reader in (read_nofollow_fd, read_lstat, read_regular):
            for path in ("../outside", "/etc/passwd", "dir/../../outside", "a\\b"):
                with self.subTest(reader=reader.__name__, path=path), self.assertRaises(RuntimeError):
                    reader(self.root, path)
            with self.subTest(reader=reader.__name__, path="fifo"), self.assertRaises(RuntimeError):
                reader(self.root, "fifo")


if __name__ == "__main__":
    unittest.main()
