import importlib.util
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_site", ROOT / "scripts/check_site.py")
site_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_check)


class PublicationTests(unittest.TestCase):
    def test_bilingual_source_candidate_and_changelog_are_valid(self):
        result = subprocess.run(
            [
                sys.executable,
                ROOT / "scripts/check_publication.py",
                "--tag",
                "v"
                + re.search(
                    r'^VERSION = "([0-9.]+)"$', (ROOT / "worktree-kit/manager.py").read_text(), re.M
                )[1],
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("bilingual pages", result.stdout)

    def test_wrong_release_tag_is_rejected(self):
        result = subprocess.run(
            [sys.executable, ROOT / "scripts/check_publication.py", "--tag", "v99.0.0"],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Tag must match", result.stderr)

    def test_release_archive_omits_site_and_build_dependencies(self):
        with tempfile.TemporaryDirectory(prefix="wtk-release-") as directory:
            destination = Path(directory) / "candidate.tar.gz"
            subprocess.run(
                [sys.executable, ROOT / "scripts/build_release.py", "--output", destination],
                check=True,
                capture_output=True,
            )
            with tarfile.open(destination) as archive:
                for member in archive.getmembers():
                    path = PurePosixPath(member.name)
                    self.assertEqual(path.parts[0], "ddev-worktree-kit")
                    self.assertFalse(
                        set(path.parts) & {"site", ".cache", ".github", "scripts", "tests", ".git"}
                    )
                    self.assertNotIn(
                        path.name, ("requirements-docs.txt", "mkdocs.yml", "mkdocs.uk.yml")
                    )
                    self.assertTrue(member.isfile())

    def fixture(self, directory, link):
        root = Path(directory)
        (root / "uk").mkdir()
        (root / "index.html").write_text(f'<html lang="en"><a href="{link}">Українська</a></html>')
        (root / "uk/index.html").write_text(
            '<html lang="uk"><a id="help" href="../">English</a></html>'
        )
        return root

    def test_language_links_work_under_a_github_project_subpath(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory, "/ddev-worktree-kit/uk/#help")
            pages, links = site_check.check_site(
                root, "https://example.github.io/ddev-worktree-kit/"
            )
            self.assertEqual((pages, links), (2, 2))

    def test_root_language_link_cannot_escape_the_project_subpath(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory, "/uk/")
            with self.assertRaisesRegex(ValueError, "project subpath"):
                site_check.check_site(root, "https://example.github.io/ddev-worktree-kit/")

    def test_broken_generated_anchor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory, "uk/#missing")
            with self.assertRaisesRegex(ValueError, "Missing anchor"):
                site_check.check_site(root, "http://localhost/")
