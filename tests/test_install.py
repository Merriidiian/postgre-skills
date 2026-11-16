import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts" / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.package = self.base / "package"
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.source = self.package / "skills" / "example-skill"
        (self.source / "references").mkdir(parents=True)
        (self.source / "SKILL.md").write_text(
            '---\nname: example-skill\ndescription: "Example"\n---\n# Instructions\n'
        )
        (self.source / "references" / "data.md").write_text("reference content\n")

    def run_install(self, tool="codex", dry_run=False):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.package, tool, self.project, dry_run)

    def test_copies_entire_skill_for_each_tool_and_is_idempotent(self):
        for tool, folder in installer.DIRECTORIES.items():
            # Each client gets an independent project in this test.
            self.project = self.base / tool
            self.project.mkdir()
            self.run_install(tool)
            target = self.project / folder / "skills" / "example-skill"
            self.assertEqual((target / "references" / "data.md").read_text(), "reference content\n")
            first_mtime = (target / "SKILL.md").stat().st_mtime_ns
            self.run_install(tool)
            self.assertEqual((target / "SKILL.md").stat().st_mtime_ns, first_mtime)

    def test_dry_run_creates_nothing(self):
        self.run_install(dry_run=True)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_conflict_preserves_existing_files_and_preflights_all_skills(self):
        first = self.package / "skills" / "aaa-skill"
        first.mkdir()
        (first / "SKILL.md").write_text("first skill\n")
        target = self.project / ".agents" / "skills" / "example-skill"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("existing user content\n")
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertEqual((target / "SKILL.md").read_text(), "existing user content\n")
        self.assertFalse((target.parent / "aaa-skill").exists())

    def test_cursor_reuses_compatible_installation(self):
        self.run_install("codex")
        self.run_install("cursor")
        self.assertFalse((self.project / ".cursor").exists())

    def test_cursor_rejects_conflicting_compatible_skill(self):
        target = self.project / ".claude" / "skills" / "example-skill"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("different skill\n")
        with self.assertRaises(ValueError):
            self.run_install("cursor")
        self.assertFalse((self.project / ".cursor").exists())

    def test_destination_symlink_is_not_followed(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.project / ".agents").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_source_symlink_is_not_followed(self):
        secret = self.base / "private.txt"
        secret.write_text("must not be copied\n")
        (self.source / "reference-link").symlink_to(secret)
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertEqual(list(self.project.iterdir()), [])

    def test_bundle_discovers_repository_skill_folders(self):
        bundle = self.base / "bundle"
        import shutil
        shutil.copytree(self.package / "skills", bundle / "first-repo" / "skills")
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(bundle, "claude", self.project)
        self.assertTrue((self.project / ".claude/skills/example-skill/SKILL.md").is_file())

    def test_user_scope_uses_client_directory_without_changing_real_home(self):
        user = self.base / "test-user"
        user.mkdir()
        with patch.object(installer.Path, "home", return_value=user), patch.object(
            installer, "__file__", str(self.package / "scripts" / "install.py")
        ), contextlib.redirect_stdout(io.StringIO()):
            code = installer.main(["--tool", "claude", "--user"])
        self.assertEqual(code, 0)
        self.assertTrue((user / ".claude/skills/example-skill/SKILL.md").is_file())

    def test_missing_project_fails_without_creating_it(self):
        missing = self.base / "missing"
        with contextlib.redirect_stderr(io.StringIO()):
            code = installer.main(["--tool", "codex", "--project", str(missing)])
        self.assertEqual(code, 1)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
