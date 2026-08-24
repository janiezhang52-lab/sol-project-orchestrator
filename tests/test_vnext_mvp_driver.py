from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
DRIVER_PATH = REPO_ROOT / "release" / "sol-project-orchestrator" / "scripts" / "sol_driver.py"
SPEC = importlib.util.spec_from_file_location("sol_vnext_mvp_driver", DRIVER_PATH)
assert SPEC is not None and SPEC.loader is not None
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


def init_request(
    root: Path,
    *,
    objective: str = "hello",
    project_id: str = "project-hello",
) -> dict:
    return {
        "schema": driver.REQUEST_SCHEMA,
        "kind": "INIT",
        "objective": objective,
        "project": {
            "project_id": project_id,
            "host_id": "local",
            "root": str(root.resolve()),
            "sol_thread_id": "thread-sol",
            "is_git_repository": False,
            "fresh_asserted": True,
        },
    }


def observation(action: dict, tool: str, result) -> dict:
    return {
        "schema": driver.REQUEST_SCHEMA,
        "kind": "OBSERVATION",
        "action_id": action["action_id"],
        "observation_id": action["observation_id"],
        "tool": tool,
        "result": result,
    }


def user_input(text: str) -> dict:
    return {
        "schema": driver.REQUEST_SCHEMA,
        "kind": "USER_INPUT",
        "text": text,
        "source_thread_id": "thread-sol",
    }


def advance_driver(root: Path, request: dict, *, project_id: str | None = "project-hello") -> dict:
    return driver.advance(root, request, project_id=project_id)


def list_threads_result(*entries: dict) -> dict:
    return {
        "threads": list(entries),
        "pinnedThreads": [],
        "unavailableHosts": [],
        "unavailableSources": [],
    }


def agent_message(text: str, *, user_text: str | None = None) -> dict:
    items = []
    if user_text is not None:
        items.append({"type": "userMessage", "text": user_text})
    items.append({"type": "agentMessage", "text": text})
    return {
        "turns": [
            {
                "status": "completed",
                "items": items,
            }
        ],
        "page": {"hasMore": False, "nextCursor": None, "order": "newest_first"},
    }


def wait_result(thread_id: str, cursor: str) -> dict:
    return {
        "timedOut": False,
        "polls": [
            {
                "cursor": cursor,
                "thread": {
                    "id": thread_id,
                    "hostId": "local",
                    "status": {"type": "idle"},
                },
                "latestTurn": {"status": "completed"},
            }
        ],
        "errors": [],
    }


def complete_sol_title(
    root: Path,
    response: dict,
    *,
    project_id: str = "project-hello",
) -> dict:
    title = response["next_action"]
    response = advance_driver(
        root,
        observation(title, "set_thread_title", {"threadId": "thread-sol"}),
        project_id=project_id,
    )
    readback = response["next_action"]
    return advance_driver(
        root,
        observation(
            readback,
            "list_threads",
            list_threads_result(
                {
                    "id": "thread-sol",
                    "projectId": project_id,
                    "hostId": "local",
                    "cwd": str(root),
                    "title": driver.SOL_TITLE,
                    "kind": "codex",
                }
            ),
        ),
        project_id=project_id,
    )


class VNextMvpDriverContractTests(unittest.TestCase):
    def setUp(self):
        self._state_temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._state_temporary.cleanup)
        self.state_home = Path(self._state_temporary.name).resolve()
        state_patch = mock.patch.object(driver, "STATE_HOME", self.state_home)
        state_patch.start()
        self.addCleanup(state_patch.stop)

    def new_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name).resolve()

    def ledger_rows(self, root: Path, sql: str, *, project_id: str = "project-hello"):
        connection = sqlite3.connect(driver._ledger_path(root, project_id))
        try:
            connection.row_factory = sqlite3.Row
            return connection.execute(sql).fetchall()
        finally:
            connection.close()

    def test_relative_codex_home_falls_back_to_absolute_default_state_home(self):
        with mock.patch.dict(os.environ, {"CODEX_HOME": "relative-codex-home"}):
            expected = (
                Path.home()
                / ".codex"
                / "state"
                / "sol-project-orchestrator"
                / "v1"
            )
            self.assertEqual(driver._default_state_home(), expected)
            self.assertTrue(driver._default_state_home().is_absolute())

    def test_validate_missing_external_ledger_is_read_only(self):
        root = self.new_root()
        before_project = list(root.rglob("*"))
        before_state = list(self.state_home.rglob("*"))

        result = driver.validate_ledger(root, project_id="project-hello")

        self.assertEqual(result, {"valid": False, "errors": ["ledger:not_found"]})
        self.assertEqual(list(root.rglob("*")), before_project)
        self.assertEqual(list(self.state_home.rglob("*")), before_state)

    def test_external_locator_is_required_by_public_driver_api(self):
        advance_signature = inspect.signature(driver.advance)
        validate_signature = inspect.signature(driver.validate_ledger)
        self.assertEqual(
            advance_signature.parameters["project_id"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        self.assertEqual(
            validate_signature.parameters["project_id"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )

    def test_git_init_creates_no_project_local_control_artifact(self):
        root = self.new_root()
        subprocess.run(
            ["git", "init", "--quiet", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        before = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        request = init_request(root)
        request["project"]["is_git_repository"] = True

        response = advance_driver(root, request)

        after = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(response["state"], "TITLE_sol")
        self.assertEqual(before, after)
        self.assertFalse((root / ".sol").exists())
        self.assertEqual(len(list(self.state_home.rglob("sol-mvp-v1.sqlite3"))), 1)

    def test_cli_advance_and_validate_share_the_external_project_locator(self):
        root = self.new_root()
        codex_home = self.new_root()
        request_path = codex_home / "request.json"
        request_path.write_text(
            json.dumps(init_request(root), ensure_ascii=False),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(codex_home)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        advance = subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER_PATH),
                "advance",
                "--project-root",
                str(root),
                "--project-id",
                "project-hello",
                "--request",
                str(request_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        validation = subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER_PATH),
                "validate",
                "--project-root",
                str(root),
                "--project-id",
                "project-hello",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )

        self.assertEqual(json.loads(advance.stdout)["state"], "TITLE_sol")
        self.assertTrue(json.loads(validation.stdout)["valid"])
        self.assertFalse((root / ".sol").exists())
        self.assertEqual(
            len(
                list(
                    (codex_home / "state" / "sol-project-orchestrator" / "v1").rglob(
                        driver.LEDGER_FILENAME
                    )
                )
            ),
            1,
        )

    def test_cli_ascii_stdio_emits_ascii_json_that_round_trips_sol_title(self):
        root = self.new_root()
        codex_home = self.new_root()
        request_path = codex_home / "request.json"
        request_path.write_text(
            json.dumps(init_request(root), ensure_ascii=False),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(codex_home)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONIOENCODING"] = "ascii:strict"

        missing = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-B",
                str(DRIVER_PATH),
                "validate",
                "--project-root",
                str(root),
                "--project-id",
                "project-hello",
            ],
            capture_output=True,
            env=environment,
        )
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(
            json.loads(missing.stdout.decode("ascii", errors="strict")),
            {"valid": False, "errors": ["ledger:not_found"]},
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-B",
                str(DRIVER_PATH),
                "advance",
                "--project-root",
                str(root),
                "--project-id",
                "project-hello",
                "--request",
                str(request_path),
            ],
            capture_output=True,
            env=environment,
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr.decode("ascii", errors="backslashreplace"),
        )
        stdout = completed.stdout.decode("ascii", errors="strict")
        self.assertTrue(stdout)
        self.assertTrue(all(ord(character) < 128 for character in stdout))
        payload = json.loads(stdout)
        self.assertEqual(payload["state"], "TITLE_sol")
        self.assertEqual(payload["next_action"]["args"]["title"], driver.SOL_TITLE)

    def test_external_locator_is_stable_and_shared_by_git_and_non_git_projects(self):
        root = self.new_root()
        before = list(root.rglob("*"))
        first = driver._project_state_key("project-hello")
        second = driver._project_state_key("project-hello")
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

        response = advance_driver(root, init_request(root))
        self.assertEqual(response["state"], "TITLE_sol")
        self.assertFalse((root / ".sol").exists())
        self.assertEqual(list(root.rglob("*")), before)
        self.assertTrue(driver._ledger_path(root, "project-hello").is_file())

    def test_same_project_id_at_a_different_root_cannot_fork_a_second_ledger(self):
        first_root = self.new_root()
        second_root = self.new_root()
        advance_driver(first_root, init_request(first_root))
        ledger = driver._ledger_path(first_root, "project-hello")
        before = ledger.read_bytes()

        with self.assertRaisesRegex(driver.RequestRejected, "INIT_IDENTITY_CONFLICT"):
            advance_driver(second_root, init_request(second_root))

        self.assertEqual(driver._ledger_path(second_root, "project-hello"), ledger)
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(len(list(self.state_home.rglob(driver.LEDGER_FILENAME))), 1)

    def test_missing_or_mismatched_locator_project_id_rejects_before_any_write(self):
        for supplied, expected in (
            (None, "project_id:non_empty_string_required"),
            ("different-project", "project_id:mismatch"),
        ):
            with self.subTest(supplied=supplied):
                root = self.new_root()
                before_project = sorted(path.relative_to(root) for path in root.rglob("*"))
                before_state = sorted(path.relative_to(self.state_home) for path in self.state_home.rglob("*"))
                with self.assertRaisesRegex(driver.RequestRejected, expected):
                    advance_driver(root, init_request(root), project_id=supplied)
                after_project = sorted(path.relative_to(root) for path in root.rglob("*"))
                after_state = sorted(path.relative_to(self.state_home) for path in self.state_home.rglob("*"))
                self.assertEqual(after_project, before_project)
                self.assertEqual(after_state, before_state)

    def test_followup_with_wrong_project_id_cannot_open_or_fork_the_run(self):
        root = self.new_root()
        advance_driver(root, init_request(root))
        before = self.ledger_rows(root, "SELECT phase,revision FROM run WHERE singleton=1")[0]

        with self.assertRaisesRegex(driver.RequestRejected, "ledger:not_found"):
            advance_driver(
                root,
                {"schema": driver.REQUEST_SCHEMA, "kind": "TICK"},
                project_id="wrong-project",
            )

        after = self.ledger_rows(root, "SELECT phase,revision FROM run WHERE singleton=1")[0]
        self.assertEqual(dict(after), dict(before))
        self.assertEqual(len(list(self.state_home.rglob(driver.LEDGER_FILENAME))), 1)

    def test_legacy_project_local_ledger_is_not_migrated_or_forked(self):
        root = self.new_root()
        legacy = root / driver.LEDGER_RELATIVE
        legacy.parent.mkdir()
        legacy.write_bytes(b"frozen-0.3-ledger")

        with self.assertRaisesRegex(
            driver.RequestRejected,
            "LEGACY_LEDGER_PRESENT_USE_FROZEN_0_3_OR_START_FRESH_PROJECT",
        ):
            advance_driver(root, init_request(root))

        self.assertEqual(legacy.read_bytes(), b"frozen-0.3-ledger")
        self.assertEqual(list(self.state_home.rglob("sol-mvp-v1.sqlite3")), [])

    def test_unknown_path_presence_never_counts_as_absent(self):
        with mock.patch.object(driver.os, "lstat", side_effect=PermissionError("denied")):
            with self.assertRaisesRegex(driver.RequestRejected, "ledger:path_presence_unknown"):
                driver._path_present(Path("unreadable"))

    def test_unreadable_legacy_location_cannot_create_an_external_fork(self):
        root = self.new_root()
        legacy = root / driver.LEDGER_RELATIVE
        original = driver._path_present

        def guarded_presence(path: Path) -> bool:
            if path == legacy:
                raise driver.RequestRejected("ledger:path_presence_unknown")
            return original(path)

        with mock.patch.object(driver, "_path_present", side_effect=guarded_presence):
            with self.assertRaisesRegex(driver.RequestRejected, "ledger:path_presence_unknown"):
                advance_driver(root, init_request(root))

        self.assertFalse((root / ".sol").exists())
        self.assertEqual(list(self.state_home.rglob(driver.LEDGER_FILENAME)), [])

    def test_unrelated_project_dot_sol_content_is_left_untouched(self):
        root = self.new_root()
        user_file = root / ".sol" / "user-owned.txt"
        user_file.parent.mkdir()
        user_file.write_bytes(b"user-owned")

        response = advance_driver(root, init_request(root))

        self.assertEqual(response["state"], "TITLE_sol")
        self.assertEqual(user_file.read_bytes(), b"user-owned")
        self.assertFalse((root / driver.LEDGER_RELATIVE).exists())
        self.assertTrue(driver._ledger_path(root, "project-hello").is_file())

    def test_local_and_external_ledgers_are_rejected_as_ambiguous(self):
        root = self.new_root()
        advance_driver(root, init_request(root))
        external = driver._ledger_path(root, "project-hello")
        external_before = external.read_bytes()
        legacy = root / driver.LEDGER_RELATIVE
        legacy.parent.mkdir()
        legacy.write_bytes(b"unexpected-local-ledger")

        with self.assertRaisesRegex(driver.RequestRejected, "AMBIGUOUS_LEDGER_LOCATIONS"):
            advance_driver(root, {"schema": driver.REQUEST_SCHEMA, "kind": "TICK"})
        with self.assertRaisesRegex(driver.RequestRejected, "AMBIGUOUS_LEDGER_LOCATIONS"):
            driver.validate_ledger(root, project_id="project-hello")

        self.assertEqual(external.read_bytes(), external_before)
        self.assertEqual(legacy.read_bytes(), b"unexpected-local-ledger")

    def test_state_home_inside_project_or_dot_git_rejects_before_write(self):
        root = self.new_root()
        cases = (
            (root / "control-state", "ledger:state_home_inside_project"),
            (self.state_home / ".git" / "control-state", "ledger:state_home_dot_git_forbidden"),
        )
        for unsafe_state_home, expected in cases:
            with self.subTest(expected=expected):
                with mock.patch.object(driver, "STATE_HOME", unsafe_state_home):
                    with self.assertRaisesRegex(driver.RequestRejected, expected):
                        advance_driver(root, init_request(root))
                self.assertFalse((root / ".sol").exists())
                self.assertFalse(unsafe_state_home.exists())

    def test_resolved_ledger_directory_inside_project_rejects_before_write(self):
        root = self.state_home / "projects"
        root.mkdir()
        before = list(root.rglob("*"))

        with self.assertRaisesRegex(driver.RequestRejected, "ledger:directory_inside_project"):
            advance_driver(root, init_request(root))

        self.assertEqual(list(root.rglob("*")), before)
        self.assertFalse(any(root.rglob(driver.LEDGER_FILENAME)))

    def test_symlinked_state_parent_into_project_is_rejected_before_write(self):
        root = self.new_root()
        target = root / "redirected-state"
        target.mkdir()
        outside = self.new_root()
        linked_parent = outside / "codex-home-link"
        try:
            os.symlink(target, linked_parent, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        unsafe_state_home = linked_parent / "state" / "sol-project-orchestrator" / "v1"
        before = sorted(path.relative_to(root) for path in root.rglob("*"))

        with mock.patch.object(driver, "STATE_HOME", unsafe_state_home):
            with self.assertRaisesRegex(driver.RequestRejected, "ledger:path_link_forbidden"):
                advance_driver(root, init_request(root))

        after = sorted(path.relative_to(root) for path in root.rglob("*"))
        self.assertEqual(after, before)

    def seed_upstream_evidence(
        self,
        connection,
        *,
        stage: str,
        status: str,
        summary: str,
        role: str,
        thread_id: str,
    ):
        now = driver._now()
        connection.execute(
            "UPDATE roles SET thread_id=?,host_id='local',state='COMPLETED',updated_at=? WHERE role=?",
            (thread_id, now, role),
        )
        send = driver._insert_action(
            connection,
            logical_key=f"send:{stage}",
            action_kind="MUTATION",
            operation=f"SEND_{stage.upper()}",
            tool="send_message_to_thread",
            args={"threadId": thread_id, "hostId": "local", "prompt": f"seed {stage}"},
            target_role=role,
            target_thread_id=thread_id,
        )
        connection.execute(
            "UPDATE actions SET status='COMMITTED' WHERE action_id=?",
            (send["action_id"],),
        )
        raw_sha256 = driver._digest_text(f"seed-observation:{stage}")
        connection.execute(
            "INSERT INTO stage_results(stage,status,summary,owner_role,owner_thread_id,"
            "observation_sha256,created_at) VALUES(?,?,?,?,?,?,?)",
            (stage, status, summary, role, thread_id, raw_sha256, now),
        )
        return send, raw_sha256

    def test_init_releases_one_mutation_then_only_reconciles(self):
        root = self.new_root()

        first = advance_driver(root, init_request(root))
        second = advance_driver(root, {"schema": driver.REQUEST_SCHEMA, "kind": "TICK"})

        self.assertEqual(first["state"], "TITLE_sol")
        self.assertEqual(first["next_action"]["kind"], "HOST_MUTATE")
        self.assertEqual(first["next_action"]["tool"], "set_thread_title")
        self.assertEqual(second["next_action"]["kind"], "HOST_OBSERVE")
        self.assertEqual(second["next_action"]["tool"], "list_threads")
        self.assertEqual(second["next_action"]["args"], {"limit": 50})
        self.assertEqual(first["next_action"]["action_id"], second["next_action"]["action_id"])

        rows = self.ledger_rows(
            root,
            "SELECT logical_key, emit_count, status FROM actions WHERE action_kind='MUTATION'",
        )
        self.assertEqual(
            [dict(row) for row in rows],
            [{"logical_key": "title:sol", "emit_count": 1, "status": "PENDING"}],
        )

    def test_two_concurrent_init_calls_release_one_mutation_and_one_observation(self):
        root = self.new_root()
        request = init_request(root)
        barrier = threading.Barrier(2, timeout=10)

        def invoke():
            barrier.wait()
            return advance_driver(root, copy.deepcopy(request))

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(invoke) for _ in range(2)]
            outcomes = [future.result(timeout=20) for future in futures]

        self.assertEqual(
            sorted(item["next_action"]["kind"] for item in outcomes),
            ["HOST_MUTATE", "HOST_OBSERVE"],
        )
        self.assertEqual(
            len({item["next_action"]["action_id"] for item in outcomes}),
            1,
        )
        rows = self.ledger_rows(
            root,
            "SELECT logical_key, emit_count FROM actions WHERE action_kind='MUTATION'",
        )
        self.assertEqual(
            [dict(row) for row in rows],
            [{"logical_key": "title:sol", "emit_count": 1}],
        )

    def test_progress_claim_fields_are_rejected_before_any_write(self):
        for forbidden in ("receipts", "cursor", "phase"):
            with self.subTest(forbidden=forbidden):
                root = self.new_root()
                request = init_request(root)
                request[forbidden] = [] if forbidden == "receipts" else "caller-owned"

                with self.assertRaisesRegex(driver.RequestRejected, r"request:unexpected"):
                    advance_driver(root, request)

                self.assertFalse((root / ".sol").exists())

    def test_unknown_create_stops_after_three_observations_without_resend(self):
        root = self.new_root()
        response = advance_driver(root, init_request(root))
        response = complete_sol_title(root, response)
        mutation = response["next_action"]
        self.assertEqual(mutation["kind"], "HOST_MUTATE")

        observed_kinds = []
        response = advance_driver(root, observation(mutation, "create_thread", {}))
        self.assertEqual(response["next_action"]["args"], {"limit": 50})
        observed_kinds.append(response["next_action"]["kind"])
        reconciliation_snapshots = (list_threads_result(), list_threads_result())
        for snapshot in reconciliation_snapshots:
            reconciliation = response["next_action"]
            response = advance_driver(
                root,
                observation(reconciliation, "list_threads", snapshot),
            )
            observed_kinds.append(response["next_action"]["kind"])

        self.assertEqual(observed_kinds, ["HOST_OBSERVE", "HOST_OBSERVE", "WAIT_USER"])
        self.assertEqual(response["state"], "NEEDS_INPUT")
        self.assertNotIn("HOST_MUTATE", observed_kinds)

        tick = advance_driver(root, {"schema": driver.REQUEST_SCHEMA, "kind": "TICK"})
        self.assertEqual(tick["state"], "NEEDS_INPUT")
        self.assertEqual(tick["next_action"]["kind"], "WAIT_USER")
        rows = self.ledger_rows(
            root,
            "SELECT emit_count, observation_count, status FROM actions WHERE logical_key='create:executor'",
        )
        self.assertEqual(
            [dict(row) for row in rows],
            [{"emit_count": 1, "observation_count": 3, "status": "UNKNOWN"}],
        )

        continued = advance_driver(root, user_input("继续核对"))
        self.assertEqual(continued["next_action"]["kind"], "HOST_OBSERVE")
        self.assertEqual(continued["next_action"]["args"], {"limit": 50})
        after = self.ledger_rows(
            root,
            "SELECT emit_count,observation_count,observation_limit FROM actions "
            "WHERE logical_key='create:executor'",
        )[0]
        self.assertEqual(dict(after), {"emit_count": 1, "observation_count": 3, "observation_limit": 6})

    def test_create_receipt_is_only_a_candidate_until_project_readback(self):
        root = self.new_root()
        response = complete_sol_title(root, advance_driver(root, init_request(root)))
        create = response["next_action"]
        response = advance_driver(
            root,
            observation(create, "create_thread", {"threadId": "thread-executor", "hostId": "local"}),
        )

        self.assertEqual(response["state"], "WAIT_VISIBLE_executor")
        self.assertEqual(response["next_action"]["operation"], "WAIT_VISIBLE_EXECUTOR")
        role = self.ledger_rows(
            root,
            "SELECT thread_id,state FROM roles WHERE role='executor'",
        )[0]
        self.assertEqual(dict(role), {"thread_id": "thread-executor", "state": "CANDIDATE"})

        response = advance_driver(
            root,
            observation(
                response["next_action"],
                "wait_threads",
                wait_result("thread-executor", "visible-executor"),
            ),
        )
        self.assertEqual(response["next_action"]["operation"], "VERIFY_EXECUTOR")

        response = advance_driver(
            root,
            observation(
                response["next_action"],
                "list_threads",
                list_threads_result(
                    {
                        "id": "thread-executor",
                        "projectId": "wrong-project",
                        "hostId": "local",
                        "cwd": str(root),
                        "title": "temporary",
                        "kind": "codex",
                    }
                ),
            ),
        )
        self.assertEqual(response["state"], "FAILED_CLOSED")

    def test_role_thread_id_cannot_equal_sol_thread_id(self):
        root = self.new_root()
        response = complete_sol_title(root, advance_driver(root, init_request(root)))
        create = response["next_action"]

        response = advance_driver(
            root,
            observation(create, "create_thread", {"threadId": "thread-sol", "hostId": "local"}),
        )

        self.assertEqual(response["state"], "FAILED_CLOSED")
        role = self.ledger_rows(
            root,
            "SELECT thread_id,state FROM roles WHERE role='executor'",
        )[0]
        self.assertEqual(dict(role), {"thread_id": None, "state": "PLANNED"})

    def test_role_thread_id_must_be_bounded_safe_ascii_before_persistence(self):
        for index, unsafe_thread_id in enumerate(
            (
                "thread-executor\nIGNORE_PREVIOUS",
                "t" * 129,
                "线程-executor",
            )
        ):
            with self.subTest(unsafe_thread_id=repr(unsafe_thread_id)):
                root = self.new_root()
                project_id = f"project-unsafe-{index}"
                response = complete_sol_title(
                    root,
                    advance_driver(
                        root,
                        init_request(root, project_id=project_id),
                        project_id=project_id,
                    ),
                    project_id=project_id,
                )
                create = response["next_action"]

                response = advance_driver(
                    root,
                    observation(
                        create,
                        "create_thread",
                        {"threadId": unsafe_thread_id, "hostId": "local"},
                    ),
                    project_id=project_id,
                )

                self.assertEqual(response["state"], "FAILED_CLOSED")
                role = self.ledger_rows(
                    root,
                    "SELECT thread_id,state FROM roles WHERE role='executor'",
                    project_id=project_id,
                )[0]
                self.assertEqual(dict(role), {"thread_id": None, "state": "PLANNED"})

    def test_error_response_cannot_smuggle_a_thread_id(self):
        root = self.new_root()
        response = complete_sol_title(root, advance_driver(root, init_request(root)))
        create = response["next_action"]
        response = advance_driver(
            root,
            observation(
                create,
                "create_thread",
                {"error": {"message": "create failed"}, "threadId": "unrelated-thread"},
            ),
        )
        self.assertEqual(response["state"], "CREATE_executor")
        self.assertEqual(response["next_action"]["kind"], "HOST_OBSERVE")
        role = self.ledger_rows(
            root,
            "SELECT thread_id,state FROM roles WHERE role='executor'",
        )[0]
        self.assertEqual(dict(role), {"thread_id": None, "state": "PLANNED"})

    def test_observation_replay_is_noop_but_same_id_conflict_fails_closed(self):
        root = self.new_root()
        response = complete_sol_title(root, advance_driver(root, init_request(root)))
        create = response["next_action"]
        first_request = observation(create, "create_thread", {})
        first = advance_driver(root, first_request)
        replay = advance_driver(root, copy.deepcopy(first_request))
        self.assertEqual(first, replay)

        conflicting = copy.deepcopy(first_request)
        conflicting["result"] = {"threadId": "different"}
        terminal = advance_driver(root, conflicting)
        self.assertEqual(terminal["state"], "FAILED_CLOSED")

    def test_hash_character_in_path_does_not_break_read_only_validation(self):
        base = self.new_root()
        root = base / "project#one"
        root.mkdir()
        response = advance_driver(root, init_request(root))
        self.assertEqual(response["next_action"]["kind"], "HOST_MUTATE")
        self.assertTrue(driver.validate_ledger(root, project_id="project-hello")["valid"])

    def test_linked_external_ledger_directory_is_rejected(self):
        root = self.new_root()
        outside = self.new_root()
        target = outside / "state"
        target.mkdir()
        projects = self.state_home / "projects"
        try:
            os.symlink(target, projects, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        with self.assertRaisesRegex(driver.RequestRejected, "ledger:path_link_forbidden"):
            advance_driver(root, init_request(root))
        self.assertFalse((target / "sol-mvp-v1.sqlite3").exists())

    def test_hardlinked_ledger_file_cannot_modify_an_outside_file(self):
        root = self.new_root()
        outside = self.new_root() / "outside.sqlite3"
        outside.write_bytes(b"")
        ledger = driver._ledger_path(root, "project-hello", create_parent=True)
        try:
            os.link(outside, ledger)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")

        with self.assertRaisesRegex(driver.RequestRejected, "ledger:file_hardlink_forbidden"):
            advance_driver(root, init_request(root))
        self.assertEqual(outside.read_bytes(), b"")

    def test_hardlinked_sqlite_sidecar_cannot_modify_an_outside_file(self):
        root = self.new_root()
        advance_driver(root, init_request(root))
        ledger = driver._ledger_path(root, "project-hello")
        sidecar = Path(f"{ledger}-shm")
        if sidecar.exists():
            sidecar.unlink()
        outside = self.new_root() / "outside-shm"
        outside.write_bytes(b"outside")
        try:
            os.link(outside, sidecar)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")

        with self.assertRaisesRegex(driver.RequestRejected, "ledger:sidecar_hardlink_forbidden"):
            advance_driver(root, {"schema": driver.REQUEST_SCHEMA, "kind": "TICK"})
        with self.assertRaisesRegex(driver.RequestRejected, "ledger:sidecar_hardlink_forbidden"):
            driver.validate_ledger(root, project_id="project-hello")
        self.assertEqual(outside.read_bytes(), b"outside")

    def test_closeout_after_acceptance_fail_requests_input_without_summary_injection(self):
        root = self.new_root()
        advance_driver(root, init_request(root))
        connection = driver._connect(root, "project-hello", create=False)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE actions SET status='COMMITTED' "
                "WHERE action_kind='MUTATION' AND status IN ('PENDING','UNKNOWN')"
            )
            self.seed_upstream_evidence(
                connection,
                stage="execution",
                status="COMPLETE",
                summary="EXECUTOR_INJECT",
                role="executor",
                thread_id="thread-e",
            )
            self.seed_upstream_evidence(
                connection,
                stage="acceptance",
                status="FAIL",
                summary="ACCEPTANCE_INJECT",
                role="acceptance",
                thread_id="thread-a",
            )
            prompt = driver._stage_prompt(connection, driver._run(connection), "closeout", "action-closeout")
            connection.rollback()
        finally:
            connection.close()
        self.assertIn('"status":"NEEDS_INPUT"', prompt)
        self.assertIn("acceptance 不是 PASS，本轮只能选择 NEEDS_INPUT", prompt)
        self.assertNotIn('"status":"TECHNICALLY_CLOSED"', prompt)
        self.assertNotIn("EXECUTOR_INJECT", prompt)
        self.assertNotIn("ACCEPTANCE_INJECT", prompt)

    def test_closeout_rejects_stage_row_without_matching_committed_send_evidence(self):
        root = self.new_root()
        advance_driver(root, init_request(root))
        connection = driver._connect(root, "project-hello", create=False)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE actions SET status='COMMITTED' "
                "WHERE action_kind='MUTATION' AND status IN ('PENDING','UNKNOWN')"
            )
            self.seed_upstream_evidence(
                connection,
                stage="execution",
                status="COMPLETE",
                summary="execution complete",
                role="executor",
                thread_id="thread-e",
            )
            self.seed_upstream_evidence(
                connection,
                stage="acceptance",
                status="PASS",
                summary="acceptance complete",
                role="acceptance",
                thread_id="thread-a",
            )
            connection.execute(
                "UPDATE actions SET target_thread_id='wrong-thread' WHERE logical_key='send:acceptance'"
            )
            with self.assertRaisesRegex(
                driver.LedgerConflict,
                "UPSTREAM_EVIDENCE_MISMATCH:acceptance",
            ):
                driver._stage_prompt(connection, driver._run(connection), "closeout", "action-closeout")
            connection.rollback()
        finally:
            connection.close()

    def test_init_identity_drift_is_rejected_without_poisoning_run(self):
        root = self.new_root()
        advance_driver(root, init_request(root))
        changes = (
            ("objective", "different objective"),
            ("sol_thread_id", "different-sol-thread"),
            ("is_git_repository", True),
        )
        for field, value in changes:
            with self.subTest(field=field):
                changed = init_request(root)
                if field == "objective":
                    changed["objective"] = value
                else:
                    changed["project"][field] = value
                with self.assertRaisesRegex(driver.RequestRejected, "INIT_IDENTITY_CONFLICT"):
                    advance_driver(root, changed)
        state = self.ledger_rows(root, "SELECT phase FROM run WHERE singleton=1")[0]["phase"]
        self.assertEqual(state, "TITLE_sol")
        self.assertEqual(len(list(self.state_home.rglob(driver.LEDGER_FILENAME))), 1)

    def test_list_error_cannot_confirm_sol_title(self):
        root = self.new_root()
        response = advance_driver(root, init_request(root))
        title = response["next_action"]
        response = advance_driver(
            root,
            observation(title, "set_thread_title", {"threadId": "thread-sol"}),
        )
        readback = response["next_action"]
        result = list_threads_result(
            {
                "id": "thread-sol",
                "projectId": "project-hello",
                "hostId": "local",
                "cwd": str(root),
                "title": driver.SOL_TITLE,
                "kind": "codex",
            }
        )
        result["error"] = "list failed"
        response = advance_driver(root, observation(readback, "list_threads", result))
        self.assertEqual(response["state"], "TITLE_sol")
        self.assertEqual(response["next_action"]["kind"], "HOST_OBSERVE")

    def test_sol_title_receipt_or_lost_result_reconciles_only_with_list_threads(self):
        for receipt_observed in (True, False):
            with self.subTest(receipt_observed=receipt_observed):
                root = self.new_root()
                project_id = f"project-title-{int(receipt_observed)}"
                response = advance_driver(
                    root,
                    init_request(root, project_id=project_id),
                    project_id=project_id,
                )
                mutation = response["next_action"]
                self.assertEqual(mutation["operation"], "TITLE_SOL")

                if receipt_observed:
                    response = advance_driver(
                        root,
                        observation(
                            mutation,
                            "set_thread_title",
                            {"threadId": "thread-sol"},
                        ),
                        project_id=project_id,
                    )
                else:
                    response = advance_driver(
                        root,
                        {"schema": driver.REQUEST_SCHEMA, "kind": "TICK"},
                        project_id=project_id,
                    )

                for observed_title in ("old title one", "old title two", driver.SOL_TITLE):
                    reconciliation = response["next_action"]
                    self.assertEqual(reconciliation["operation"], "TITLE_SOL")
                    self.assertEqual(reconciliation["kind"], "HOST_OBSERVE")
                    self.assertEqual(reconciliation["tool"], "list_threads")
                    self.assertEqual(reconciliation["args"], {"limit": 50})
                    response = advance_driver(
                        root,
                        observation(
                            reconciliation,
                            "list_threads",
                            list_threads_result(
                                {
                                    "id": "thread-sol",
                                    "projectId": project_id,
                                    "hostId": "local",
                                    "cwd": str(root),
                                    "title": observed_title,
                                    "kind": "codex",
                                }
                            ),
                        ),
                        project_id=project_id,
                    )

                self.assertEqual(response["state"], "CREATE_executor")
                self.assertEqual(response["next_action"]["operation"], "CREATE_EXECUTOR")
                action = self.ledger_rows(
                    root,
                    "SELECT emit_count FROM actions WHERE logical_key='title:sol'",
                    project_id=project_id,
                )[0]
                self.assertEqual(action["emit_count"], 1)

    def test_json_text_host_envelope_is_decoded_exactly_once(self):
        root = self.new_root()
        response = advance_driver(root, init_request(root))
        title = response["next_action"]
        response = advance_driver(
            root,
            observation(title, "set_thread_title", json.dumps({"threadId": "thread-sol"})),
        )
        readback = response["next_action"]
        response = advance_driver(
            root,
            observation(
                readback,
                "list_threads",
                json.dumps(
                    list_threads_result(
                        {
                            "id": "thread-sol",
                            "projectId": "project-hello",
                            "hostId": "local",
                            "cwd": str(root),
                            "title": driver.SOL_TITLE,
                            "kind": "codex",
                        }
                    )
                ),
            ),
        )
        self.assertEqual(response["next_action"]["operation"], "CREATE_EXECUTOR")
        nested = json.dumps(json.dumps({"threadId": "forged"}))
        self.assertIsInstance(driver._decode_host_result_once(nested), str)
        duplicate = driver._decode_host_result_once('{"threadId":"one","threadId":"two"}')
        self.assertEqual(duplicate["isError"], True)

    def test_tool_failure_is_bounded_and_never_releases_title_again(self):
        root = self.new_root()
        response = advance_driver(root, init_request(root))
        kinds = []
        for _ in range(6):
            action = response["next_action"]
            response = advance_driver(
                root,
                {
                    "schema": driver.REQUEST_SCHEMA,
                    "kind": "TOOL_FAILURE",
                    "action_id": action["action_id"],
                    "observation_id": action["observation_id"],
                    "tool": action["tool"],
                    "error": "host tool unavailable",
                },
            )
            kinds.append(response["next_action"]["kind"])
        self.assertEqual(kinds, ["HOST_OBSERVE"] * 5 + ["WAIT_USER"])
        self.assertEqual(response["state"], "NEEDS_INPUT")
        self.assertEqual(
            self.ledger_rows(
                root,
                "SELECT emit_count FROM actions WHERE logical_key='title:sol'",
            )[0]["emit_count"],
            1,
        )

    def test_read_parser_rejects_errors_truncation_and_nonterminal_latest_turn(self):
        complete = agent_message("done")
        self.assertIsNotNone(driver._complete_latest_turn(complete))

        truncated = copy.deepcopy(complete)
        truncated["page"]["hasMore"] = True
        self.assertIsNone(driver._complete_latest_turn(truncated))

        legacy_top_level = copy.deepcopy(complete)
        legacy_top_level.pop("page")
        legacy_top_level["hasMore"] = False
        legacy_top_level["nextCursor"] = None
        self.assertIsNone(driver._complete_latest_turn(legacy_top_level))

        errored = copy.deepcopy(complete)
        errored["error"] = "read failed"
        self.assertIsNone(driver._complete_latest_turn(errored))

        in_progress = copy.deepcopy(complete)
        in_progress["turns"].insert(
            0,
            {"status": "inProgress", "items": [{"type": "agentMessage", "text": "later"}]}
        )
        self.assertIsNone(driver._complete_latest_turn(in_progress))

        two_turns = copy.deepcopy(complete)
        two_turns["turns"] = [
            {"status": "completed", "items": [{"type": "agentMessage", "text": "new"}]},
            {"status": "completed", "items": [{"type": "agentMessage", "text": "old"}]},
        ]
        newest = driver._complete_latest_turn(two_turns)
        self.assertEqual(driver._typed_texts(newest, "agentMessage"), ["new"])

    def test_stage_parser_treats_non_string_status_as_incomplete(self):
        action_id = "a" * 64
        malformed = agent_message(
            "SOL_EXECUTION_RESULT_V1\n"
            + '{"action_id":"'
            + action_id
            + '","stage":"execution","status":[],"summary":"bad"}'
        )
        self.assertIsNone(driver._parse_stage_result(malformed, "execution", action_id))
        stale = agent_message(
            "SOL_EXECUTION_RESULT_V1\n"
            + '{"action_id":"stale","stage":"execution","status":"COMPLETE","summary":"bad"}'
        )
        self.assertIsNone(driver._parse_stage_result(stale, "execution", action_id))

    def test_nested_recovered_command_failure_does_not_poison_valid_stage_result(self):
        action_id = "b" * 64
        result = agent_message(
            "SOL_EXECUTION_RESULT_V1\n"
            + json.dumps(
                {
                    "action_id": action_id,
                    "stage": "execution",
                    "status": "COMPLETE",
                    "summary": "recovered and completed",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        result["turns"][0]["items"].insert(
            0,
            {
                "type": "commandExecution",
                "status": "failed",
                "error": "first command failed",
            },
        )

        parsed = driver._parse_stage_result(result, "execution", action_id)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["status"], "COMPLETE")

    def test_ui_transport_normalization_is_narrow(self):
        self.assertEqual(driver._normalize_ui_text("去执行"), "去执行")
        self.assertEqual(driver._normalize_ui_text("去执行\n"), "去执行")
        self.assertEqual(driver._normalize_ui_text("去执行\r\n"), "去执行")
        for invalid in ("去执行\r", "去执行\n\n", "去\n执行"):
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaises(driver.RequestRejected):
                    driver._normalize_ui_text(invalid)
        self.assertEqual(driver._normalize_ui_text(" 去执行 "), " 去执行 ")

    def test_hello_gold_chain_reaches_product_accepted(self):
        root = self.new_root()
        response = advance_driver(root, init_request(root, objective="hello"))
        work_id = response["work_id"]
        response = complete_sol_title(root, response)
        role_threads = {
            "executor": "thread-executor",
            "acceptance": "thread-acceptance",
            "closeout": "thread-closeout",
        }

        for role in driver.ROLE_ORDER:
            create = response["next_action"]
            self.assertEqual((create["kind"], create["operation"]), ("HOST_MUTATE", f"CREATE_{role.upper()}"))
            self.assertIn("hello", create["args"]["prompt"])
            response = advance_driver(
                root,
                observation(
                    create,
                    "create_thread",
                    {"threadId": role_threads[role], "hostId": "local"},
                ),
            )

            wait_visible = response["next_action"]
            self.assertEqual(
                (wait_visible["kind"], wait_visible["operation"]),
                ("HOST_OBSERVE", f"WAIT_VISIBLE_{role.upper()}"),
            )
            response = advance_driver(
                root,
                observation(
                    wait_visible,
                    "wait_threads",
                    wait_result(role_threads[role], f"visible-{role}"),
                ),
            )
            verify = response["next_action"]
            self.assertEqual(
                (verify["kind"], verify["operation"]),
                ("HOST_OBSERVE", f"VERIFY_{role.upper()}"),
            )
            response = advance_driver(
                root,
                observation(
                    verify,
                    "list_threads",
                    list_threads_result(
                        {
                            "id": role_threads[role],
                            "projectId": "project-hello",
                            "hostId": "local",
                            "cwd": str(root),
                            "title": "temporary",
                            "kind": "codex",
                        }
                    ),
                ),
            )

            title = response["next_action"]
            self.assertEqual((title["kind"], title["operation"]), ("HOST_MUTATE", f"TITLE_{role.upper()}"))
            response = advance_driver(
                root,
                observation(title, "set_thread_title", {"threadId": role_threads[role]}),
            )
            self.assertEqual(response["next_action"]["kind"], "HOST_OBSERVE")
            title_settle = response["next_action"]
            self.assertEqual(title_settle["tool"], "wait_threads")
            response = advance_driver(
                root,
                observation(
                    title_settle,
                    "wait_threads",
                    wait_result(role_threads[role], f"title-{role}"),
                ),
            )
            title_readback = response["next_action"]
            response = advance_driver(
                root,
                observation(
                    title_readback,
                    "list_threads",
                    list_threads_result(
                        {
                            "id": role_threads[role],
                            "projectId": "project-hello",
                            "hostId": "local",
                            "cwd": str(root),
                            "title": driver.ROLE_TITLES[role],
                        }
                    ),
                ),
            )

            wait_ready = response["next_action"]
            self.assertEqual(
                (wait_ready["kind"], wait_ready["operation"]),
                ("HOST_OBSERVE", f"WAIT_READY_{role.upper()}"),
            )
            response = advance_driver(
                root,
                observation(
                    wait_ready,
                    "wait_threads",
                    wait_result(role_threads[role], f"ready-{role}"),
                ),
            )
            ready = response["next_action"]
            self.assertEqual((ready["kind"], ready["operation"]), ("HOST_OBSERVE", f"READ_READY_{role.upper()}"))
            response = advance_driver(
                root,
                observation(
                    ready,
                    "read_thread",
                    agent_message(driver.READY_REPLIES[role], user_text=create["args"]["prompt"]),
                ),
            )

        self.assertEqual(response["state"], "READY_FOR_AUTHORIZATION")
        self.assertEqual(response["next_action"]["kind"], "WAIT_USER")
        response = advance_driver(root, user_input("去执行\n"))

        stages = (
            ("execution", "executor", "SOL_EXECUTION_RESULT_V1", "COMPLETE"),
            ("acceptance", "acceptance", "SOL_ACCEPTANCE_RESULT_V1", "PASS"),
            ("closeout", "closeout", "SOL_CLOSEOUT_RESULT_V1", "TECHNICALLY_CLOSED"),
        )
        upstream = {}
        for stage, role, marker, status in stages:
            send = response["next_action"]
            self.assertEqual((send["kind"], send["operation"]), ("HOST_MUTATE", f"SEND_{stage.upper()}"))
            self.assertIn("hello", send["args"]["prompt"])
            if stage == "closeout":
                prompt = send["args"]["prompt"]
                expected_index = {
                    "schema": "SOL_UPSTREAM_EVIDENCE_INDEX_V1",
                    "work_id": work_id,
                    "objective_sha256": driver._digest_text("hello"),
                    "host_id": "local",
                    "execution": upstream["execution"],
                    "acceptance": upstream["acceptance"],
                }
                self.assertIn(driver._json(expected_index), prompt)
                self.assertNotIn("execution complete", prompt)
                self.assertNotIn("acceptance complete", prompt)
                self.assertIn("必须独立选择 TECHNICALLY_CLOSED 或 NEEDS_INPUT", prompt)
                self.assertIn(
                    '"stage":"closeout","status":"TECHNICALLY_CLOSED"',
                    prompt,
                )
                self.assertIn(
                    '"stage":"closeout","status":"NEEDS_INPUT"',
                    prompt,
                )
                execution_read = (
                    "execution read_thread 固定参数：hostId=host_id、turnLimit=10、"
                    "includeOutputs=true、maxOutputCharsPerItem=20000"
                )
                acceptance_read = (
                    "acceptance read_thread 固定参数：hostId=host_id、turnLimit=10、"
                    "includeOutputs=true、maxOutputCharsPerItem=20000"
                )
                self.assertIn(execution_read, prompt)
                self.assertIn(acceptance_read, prompt)
                self.assertEqual(prompt.count("maxOutputCharsPerItem=20000"), 2)
                self.assertNotIn("30000", prompt)
                self.assertIn("各且仅各调用一次 read_thread", prompt)
                self.assertIn("不得重试、不得换工具", prompt)
                self.assertIn("任一路无法确认就选 NEEDS_INPUT", prompt)
                closeout_action = self.ledger_rows(
                    root,
                    "SELECT args_json,args_sha256 FROM actions WHERE logical_key='send:closeout'",
                )[0]
                self.assertEqual(closeout_action["args_json"], driver._json(send["args"]))
                self.assertEqual(
                    closeout_action["args_sha256"],
                    driver._digest_json(send["args"]),
                )
            response = advance_driver(
                root,
                observation(send, "send_message_to_thread", {"threadId": role_threads[role]}),
            )

            wait_stage = response["next_action"]
            self.assertEqual(
                (wait_stage["kind"], wait_stage["operation"]),
                ("HOST_OBSERVE", f"WAIT_RESULT_{stage.upper()}"),
            )
            response = advance_driver(
                root,
                observation(
                    wait_stage,
                    "wait_threads",
                    wait_result(role_threads[role], f"result-{stage}"),
                ),
            )
            read_result = response["next_action"]
            self.assertEqual(
                (read_result["kind"], read_result["operation"]),
                ("HOST_OBSERVE", f"READ_RESULT_{stage.upper()}"),
            )
            result_text = (
                f"{marker}\n"
                + "{"
                + f'"action_id":"{send["action_id"]}","stage":"{stage}",'
                + f'"status":"{status}","summary":"{stage} complete"'
                + "}"
            )
            stage_view = agent_message(result_text)
            stage_view["turns"].append(
                {
                    "status": "completed",
                    "items": [{"type": "agentMessage", "text": driver.READY_REPLIES[role]}],
                }
            )
            report_observation_sha256 = driver._digest_json(stage_view)
            response = advance_driver(
                root,
                observation(read_result, "read_thread", stage_view),
            )
            if stage == "closeout":
                closeout_result = self.ledger_rows(
                    root,
                    "SELECT observation_sha256 FROM stage_results WHERE stage='closeout'",
                )[0]
                self.assertEqual(
                    closeout_result["observation_sha256"],
                    report_observation_sha256,
                )
            if stage in ("execution", "acceptance"):
                upstream[stage] = {
                    "stage": stage,
                    "status": status,
                    "owner_role": role,
                    "source_thread_id": role_threads[role],
                    "send_action_id": send["action_id"],
                    "send_args_sha256": driver._digest_json(send["args"]),
                    "report_marker": marker,
                    "report_observation_sha256": report_observation_sha256,
                }

        self.assertEqual(response["state"], "AWAIT_PRODUCT_DECISION")
        self.assertEqual(response["next_action"]["kind"], "WAIT_USER")
        response = advance_driver(root, user_input("接受产品"))
        self.assertEqual(response["state"], "PRODUCT_ACCEPTED")
        self.assertEqual(response["next_action"]["kind"], "TERMINAL")

        stage_rows = self.ledger_rows(
            root,
            "SELECT stage, status FROM stage_results ORDER BY rowid",
        )
        self.assertEqual(
            [dict(row) for row in stage_rows],
            [
                {"stage": "execution", "status": "COMPLETE"},
                {"stage": "acceptance", "status": "PASS"},
                {"stage": "closeout", "status": "TECHNICALLY_CLOSED"},
            ],
        )
        self.assertEqual(
            [row["state"] for row in self.ledger_rows(root, "SELECT state FROM roles ORDER BY rowid")],
            ["COMPLETED", "COMPLETED", "COMPLETED"],
        )
        validation = driver.validate_ledger(root, project_id="project-hello")
        self.assertTrue(validation["valid"], validation)
        self.assertEqual(validation["state"], "PRODUCT_ACCEPTED")


if __name__ == "__main__":
    unittest.main()
