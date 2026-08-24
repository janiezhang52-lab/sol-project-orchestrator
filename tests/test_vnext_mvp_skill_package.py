"""Mechanical release gate for the executable VNext MVP Skill.

These tests verify package identity and the low-freedom adapter contract. They
do not replace a real Host black-box run.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "sol-project-orchestrator"
SKILL = RELEASE / "SKILL.md"
OPENAI = RELEASE / "agents" / "openai.yaml"
DRIVER = RELEASE / "scripts" / "sol_driver.py"
MANIFEST = RELEASE / "manifest.json"

EXPECTED_FILES = {
    "LICENSE",
    "LICENSES/CC-BY-NC-4.0.txt",
    "LICENSES/PolyForm-Noncommercial-1.0.0.txt",
    "SKILL.md",
    "agents/openai.yaml",
    "manifest.json",
    "scripts/sol_driver.py",
}

ALLOWED_HOST_TOOLS = {
    "create_thread",
    "set_thread_title",
    "send_message_to_thread",
    "list_threads",
    "wait_threads",
    "read_thread",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_driver():
    spec = importlib.util.spec_from_file_location("vnext_release_driver", DRIVER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class VNextMvpSkillPackageTests(unittest.TestCase):
    def test_release_file_allowlist_is_exact(self):
        actual = {
            path.relative_to(RELEASE).as_posix()
            for path in RELEASE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, EXPECTED_FILES)

    def test_manifest_mechanically_matches_release(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "sol-vnext-mvp-release-manifest-v1")
        self.assertTrue(manifest["self_excluded"])
        entries = {entry["path"]: entry for entry in manifest["files"]}
        self.assertEqual(set(entries), EXPECTED_FILES - {"manifest.json"})
        rows = []
        for relative in sorted(entries, key=lambda value: value.encode("utf-8")):
            path = RELEASE / relative
            entry = entries[relative]
            self.assertEqual(entry["bytes"], path.stat().st_size)
            self.assertEqual(entry["sha256"], sha256(path))
            rows.append(f"{relative}\0{entry['bytes']}\0{entry['sha256']}\n")
        tree = hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()
        self.assertEqual(manifest["tree_sha256"], tree)

    def test_skill_is_thin_and_routes_every_transition_to_driver(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 140)
        self.assertIn("只由", text)
        self.assertIn("next_action", text)
        self.assertIn("OBSERVATION", text)
        self.assertIn("TOOL_FAILURE", text)
        self.assertIn("不得用 `TICK` 冒充观察", text)
        for retired in ("REGISTRATION_ACK", "ACK_SCOPE", "BIND_EXISTING", "REENTRY_STOP"):
            self.assertNotIn(retired, text)

    def test_skill_has_complete_user_surface_and_honest_git_boundary(self):
        text = SKILL.read_text(encoding="utf-8")
        for phrase in (
            "立项：<非空目标>",
            "去执行",
            "接受产品",
            "需要修订",
            "拒绝产品",
            "继续核对",
            "停止",
            "项目外的唯一 SQLite 账本",
            "--project-id <projectId>",
            "不在项目内创建 `.sol/`",
        ):
            self.assertIn(phrase, text)
        for forbidden in (
            "不承诺干净的 `git status`",
            ".git/refs/codex",
            ".git/objects",
            "checkpoint",
            "SHA-1",
            "mtime",
            "归因 Host",
            "CLAIM_MUTATION",
        ):
            self.assertNotIn(forbidden, text)

    def test_skill_locks_utf8_driver_transport_and_forbids_tick_bypass(self):
        text = SKILL.read_text(encoding="utf-8")
        for command in ("advance", "validate"):
            self.assertRegex(
                text,
                rf"`[^`\n]*-X utf8 -B [^`\n]*sol_driver\.py {command}\b[^`\n]*`",
            )
        self.assertRegex(text, r"`advance` 任意非零退出[^\n]*(?:失败关闭|停止)")
        self.assertIn(
            '`validate` 的 Host outer `exit_code` 为 `1` 或 `2`，且 `stdout` 严格解析后的对象恰为 `'
            '{"valid":false,"errors":["ledger:not_found"]}`',
            text,
        )
        self.assertIn(
            "outer `1` 只兼容 Windows Host 对 child `2` 的归一化",
            text,
        )
        self.assertRegex(text, r"非严格 JSON[^\n]*(?:失败关闭|停止)")
        self.assertRegex(
            text,
            r"严格解析后的 JSON 对象任意字符串字段含 `U\+FFFD`[^\n]*(?:失败关闭|停止)",
        )
        self.assertIn(
            "存在待回填的 `HOST_MUTATE` 或 `HOST_OBSERVE` 时不得提交 `TICK`",
            text,
        )

    def test_g3_does_not_smuggle_git_forensics_or_a_second_dispatch_protocol_into_runtime(self):
        source = DRIVER.read_text(encoding="utf-8")
        for forbidden in (
            ".git/refs/codex",
            ".git/objects",
            "turn-diffs",
            "checkpoint",
            "SHA-1",
            "mtime",
            "归因 Host",
            "CLAIM_MUTATION",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("project内 .sol/**", source)

    def test_skill_observation_contract_includes_driver_nonce(self):
        text = SKILL.read_text(encoding="utf-8")
        contract = re.search(
            r'\{"schema":"sol-mvp-request-v1","kind":"OBSERVATION".*?\}',
            text,
        )
        self.assertIsNotNone(contract)
        self.assertIn('"action_id"', contract.group(0))
        self.assertIn('"observation_id"', contract.group(0))
        self.assertIn('"result"', contract.group(0))

    def test_driver_exposes_only_advance_and_validate(self):
        driver = load_driver()
        parser = driver.build_parser()
        subparsers = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
        self.assertEqual(len(subparsers), 1)
        self.assertEqual(set(subparsers[0].choices), {"advance", "validate"})
        for command in ("advance", "validate"):
            project_id_actions = [
                action
                for action in subparsers[0].choices[command]._actions
                if action.dest == "project_id"
            ]
            self.assertEqual(len(project_id_actions), 1)
            self.assertTrue(project_id_actions[0].required)

    def test_driver_host_tool_surface_is_closed(self):
        tree = ast.parse(DRIVER.read_text(encoding="utf-8"))
        seen = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in ALLOWED_HOST_TOOLS
        }
        self.assertEqual(seen, ALLOWED_HOST_TOOLS)
        source = DRIVER.read_text(encoding="utf-8")
        for forbidden in (
            "register-task",
            "bind-visible-work-order",
            "ack-registration",
            "stage-start",
            "create-original",
            "sol_control",
        ):
            self.assertNotIn(forbidden, source)

    def test_driver_uses_only_python_standard_library(self):
        tree = ast.parse(DRIVER.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertLessEqual(
            imported,
            {"__future__", "argparse", "hashlib", "json", "os", "re", "sqlite3", "sys", "time", "datetime", "pathlib"},
        )

    def test_openai_metadata_names_executable_mvp(self):
        text = OPENAI.read_text(encoding="utf-8")
        self.assertIn('display_name: "Sol 项目总控｜可执行 MVP"', text)
        self.assertIn("$sol-project-orchestrator", text)
        self.assertNotIn("窗口与唤醒候选", text)


if __name__ == "__main__":
    unittest.main()
