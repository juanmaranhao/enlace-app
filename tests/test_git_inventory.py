"""Provas com repositórios temporários, sem tocar nos projetos do usuário."""
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless

from agentic_core.git_inventory import inspect_repository, _status_counts


@skipUnless(shutil.which("git"), "Git indisponível")
class GitInventoryTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.git("init")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Fixture")
        (self.root / "tracked.txt").write_text("original", encoding="utf8")
        (self.root / ".gitignore").write_text("private.dat\n", encoding="utf8")
        self.git("add", "tracked.txt", ".gitignore")
        self.git("commit", "-m", "Fixture")

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True)
        return result.stdout.decode().strip()

    def test_counts_preserve_files_and_never_authorize_cleanup(self):
        (self.root / "tracked.txt").write_text("modified", encoding="utf8")
        (self.root / "new.txt").write_text("exclusive", encoding="utf8")
        (self.root / "private.dat").write_text("secret-content", encoding="utf8")
        result = inspect_repository(self.root, [self.base])
        self.assertEqual(result["tracked_changed"], 1)
        self.assertEqual(result["untracked_count"], 1)
        self.assertEqual(result["ignored_count"], 1)
        self.assertTrue(result["dirty"])
        self.assertFalse(result["cleanup_authorized"])
        self.assertEqual(result["head"], self.git("rev-parse", "HEAD"))
        self.assertNotIn("secret-content", str(result))
        self.assertNotIn("private.dat", str(result))
        self.assertEqual((self.root / "tracked.txt").read_text(), "modified")

    def test_external_git_directory_does_not_change_worktree_target(self):
        gitdir = self.base / "external.git"
        shutil.move(str(self.root / ".git"), str(gitdir))
        (self.root / ".git").write_text(f"gitdir: {gitdir.as_posix()}\n", encoding="utf8")
        (self.root / "tracked.txt").write_text("modified", encoding="utf8")
        result = inspect_repository(self.root, [self.base])
        self.assertEqual(result["root"], str(self.root))
        self.assertEqual(result["tracked_changed"], 1)
        self.assertEqual(result["untracked_count"], 0)

    def test_hidden_index_flags_are_retention_reason(self):
        self.git("update-index", "--assume-unchanged", "tracked.txt")
        result = inspect_repository(self.root, [self.base])
        self.assertEqual(result["hidden_index_flags"], 1)
        self.assertTrue(result["dirty"])

    def test_path_escape_is_rejected(self):
        other = self.base / "other"
        other.mkdir()
        with self.assertRaises(ValueError):
            inspect_repository(self.root, [other])

    def test_rename_is_counted_once(self):
        self.assertEqual(_status_counts("R  new\0old\0?? extra\0"), (1, 1))
