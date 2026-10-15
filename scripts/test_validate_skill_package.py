#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_skill_package.py")
SKILL_NAME = "write-wechat-article-from-minutes"


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "skill" / SKILL_NAME
        self.skill.mkdir(parents=True)
        self.write("VERSION", "1.2.3\n")
        self.write("LICENSE", "MIT License\n")
        self.set_skill()
        self.set_agents()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_skill(self, relative: str, text: str) -> Path:
        return self.write(f"skill/{SKILL_NAME}/{relative}", text)

    def set_skill(self, description: str = "Write an article.", body: str = "# Workflow\n") -> None:
        self.write_skill("SKILL.md", f"---\nname: {SKILL_NAME}\ndescription: {description}\n---\n\n{body}")

    def set_agents(self, prompt: str = f"Use ${SKILL_NAME} to write an article.") -> None:
        self.write_skill(
            "agents/openai.yaml",
            'interface:\n  display_name: "Article Writer"\n'
            '  short_description: "Write articles from meeting notes"\n'
            f'  default_prompt: "{prompt}"\n',
        )

    def run_cli(self, *args: str, error: str = "") -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--source-root", str(self.root), *args],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1 if error else 0, result.stdout + result.stderr)
        if error:
            self.assertIn(error, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        return result

    @property
    def archive(self) -> Path:
        return self.skill / f"{SKILL_NAME}.zip"

    def test_nested_docs_and_root_metadata_in_zip(self) -> None:
        self.set_skill(body="[Reference](references/facts.md#sources)\n[Example](examples/nested/article.md)\n")
        self.write_skill("references/facts.md", "[Example](../examples/nested/article.md)\n")
        self.write_skill("examples/nested/article.md", "[License](../../LICENSE)\n[Version](../../VERSION)\n")
        self.archive.write_bytes(b"old archive must not be an input")
        self.write("private.txt", "Unrelated repository files must not be packaged.")
        self.run_cli("--zip")
        with zipfile.ZipFile(self.archive) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {
                f"{SKILL_NAME}/{name}" for name in (
                    "SKILL.md", "agents/openai.yaml", "VERSION", "LICENSE",
                    "references/facts.md", "examples/nested/article.md",
                )
            })
            for name in ("VERSION", "LICENSE"):
                self.assertEqual(archive.read(f"{SKILL_NAME}/{name}"), (self.root / name).read_bytes())

    def test_version_semver(self) -> None:
        for value in ("0.0.0", "10.20.30", "1.2.3-rc.1+build.001", "1.0.0-0", "1.0.0-01a"):
            with self.subTest(version=value):
                self.write("VERSION", value + "\n")
                self.run_cli()
        for value in ("", "v1.2.3", "1.2", "01.2.3", "1.02.3", "1.2.03", "1.2.3-01", "1.2.3-", "1.2.3+", "1.2.3\n2.0.0"):
            with self.subTest(version=value):
                self.write("VERSION", value + "\n")
                self.run_cli(error="VERSION")

    def test_required_metadata_files(self) -> None:
        for name in ("VERSION", "LICENSE", f"skill/{SKILL_NAME}/SKILL.md", f"skill/{SKILL_NAME}/agents/openai.yaml"):
            with self.subTest(file=name):
                path = self.root / name
                original = path.read_bytes()
                path.unlink()
                self.run_cli(error="Required file")
                path.write_bytes(original)

    def test_description_bounds_without_required_english_phrases(self) -> None:
        for description in ("x", "x" * 1024):
            with self.subTest(length=len(description)):
                self.set_skill(description)
                self.run_cli()
        for description in ("", '"   "', "x" * 1025, "null", "[]"):
            with self.subTest(description=description[:20]):
                self.set_skill(description)
                self.run_cli(error="description")

    def test_wrong_or_missing_skill_name(self) -> None:
        self.set_skill()
        path = self.skill / "SKILL.md"
        path.write_text(path.read_text().replace(SKILL_NAME, "other-skill"))
        self.run_cli(error="name")
        path.write_text("---\ndescription: Write articles.\n---\n")
        self.run_cli(error="name")

    def test_block_scalar_description_and_prompt(self) -> None:
        self.set_skill(">-\n  Write an article from\n  meeting notes.")
        self.write_skill("agents/openai.yaml", f"interface:\n  display_name: Writer\n  short_description: Write articles\n  default_prompt: >-\n    Use ${SKILL_NAME}\n    to write an article.\n")
        self.run_cli()

    def test_agent_fields_are_real_nonempty_interface_values(self) -> None:
        for name in ("display_name", "short_description", "default_prompt"):
            for replacement in (f"  # {name}: fake", f"  {name}: \"\""):
                with self.subTest(field=name, replacement=replacement):
                    self.set_agents()
                    path = self.skill / "agents/openai.yaml"
                    lines = path.read_text().splitlines()
                    path.write_text("\n".join(replacement if line.startswith(f"  {name}:") else line for line in lines))
                    self.run_cli(error=name)
        self.set_agents()
        path = self.skill / "agents/openai.yaml"
        path.write_text(path.read_text().replace("interface:", "other:"))
        self.run_cli(error="interface")

    def test_default_prompt_invokes_exact_skill(self) -> None:
        for prompt in ("Write an article.", SKILL_NAME, f"Use ${SKILL_NAME}-other", f"Use ${SKILL_NAME}_other"):
            with self.subTest(prompt=prompt):
                self.set_agents(prompt)
                self.run_cli(error="default_prompt")

    def test_agent_comments_and_other_sections(self) -> None:
        self.write_skill("agents/openai.yaml", f'''# Agent configuration
interface: # Presentation
  display_name: Writer
# This comment does not end the interface mapping.
  short_description: Write articles
  default_prompt: 'Use ${SKILL_NAME} to write an article.'
policy:
  allow_implicit_invocation: true
''')
        self.run_cli()

    def test_missing_local_link_rejected_in_each_document_tree(self) -> None:
        for relative in ("SKILL.md", "references/check.md", "examples/check.md"):
            with self.subTest(file=relative):
                self.set_skill()
                path = self.skill / relative
                if relative == "SKILL.md":
                    self.set_skill(body="[Missing](references/missing.md)\n")
                else:
                    self.write_skill(relative, "[Missing](missing.md)\n")
                self.run_cli(error="missing.md")
                if relative != "SKILL.md":
                    path.unlink()

    def test_markdown_code_examples_not_links(self) -> None:
        self.set_skill(body='''`[Example](missing-inline.md)`
``[Example](missing-multi.md) with `backticks` ``
```md
[Example](missing-fence.md)
```
~~~md
[Example](missing-tilde.md)
~~~
<!-- [Example](missing-comment.md) -->
[Remote](https://example.com/missing.md)
[Email](mailto:editor@example.com)
[Anchor](#workflow)
''')
        self.run_cli()

    def test_real_link_after_inline_code_is_still_validated(self) -> None:
        self.set_skill(body="`[Example](ignore.md)` [Missing](missing.md)\n")
        self.run_cli(error="missing.md")

    def test_reference_links_and_encoded_paths(self) -> None:
        self.set_skill(body='[Guide][guide]\n\n[guide]: references/guide.md "Guide"\n[Space](references/a%20b.md#part)\n[Angle](<references/a b.md>)\n[Parens](references/a(b).md)\n')
        for name in ("guide.md", "a b.md", "a(b).md"):
            self.write_skill(f"references/{name}", "# Reference\n")
        self.run_cli()
        (self.skill / "references/guide.md").unlink()
        self.run_cli(error="guide.md")

    def test_links_cannot_escape_package(self) -> None:
        self.write("outside.md", "# Outside\n")
        for target in ("../../outside.md", "%2e%2e/%2e%2e/outside.md", str(self.root / "outside.md"), "file:///tmp/outside.md"):
            with self.subTest(target=target):
                self.set_skill(body=f"[Outside]({target})\n")
                self.run_cli(error="outside")

    def test_unintended_files_rejected(self) -> None:
        for name in ("secret.txt", ".DS_Store", "other.zip", "references/data.json", "examples/example.py", "examples/.hidden.md", "agents/extra.yaml"):
            with self.subTest(file=name):
                path = self.write_skill(name, "unexpected")
                self.run_cli(error="Unexpected")
                path.unlink()

    def test_symlinked_files_rejected(self) -> None:
        target = self.write("target.md", "# Target\n")
        for name in ("VERSION", "LICENSE", f"skill/{SKILL_NAME}/SKILL.md", f"skill/{SKILL_NAME}/references/link.md", f"skill/{SKILL_NAME}/{SKILL_NAME}.zip"):
            with self.subTest(file=name):
                path = self.root / name
                original = path.read_bytes() if path.exists() else None
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.unlink()
                path.symlink_to(target)
                self.run_cli(error="Symlink")
                path.unlink()
                if original is not None:
                    path.write_bytes(original)

    def test_symlinked_directory_and_dangling_symlink_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        link = self.skill / "references"
        link.symlink_to(outside, target_is_directory=True)
        self.run_cli(error="Symlink")
        link.unlink()
        link.symlink_to(self.root / "nonexistent")
        self.run_cli(error="Symlink")

    def test_staging_only_replaces_this_skill(self) -> None:
        parent = self.root / ".skill-package-staging"
        other = self.write(".skill-package-staging/another-skill/keep.txt", "keep")
        stale = self.write(f".skill-package-staging/{SKILL_NAME}/old.txt", "stale")
        self.run_cli("--keep-staging")
        self.assertEqual(other.read_text(), "keep")
        self.assertFalse(stale.exists())
        self.assertTrue((parent / SKILL_NAME / "VERSION").is_file())
        self.run_cli("--keep-staging")
        self.assertEqual(other.read_text(), "keep")

    def test_staging_symlink_rejected_without_touching_target(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_text("keep")
        (self.root / ".skill-package-staging").symlink_to(outside, target_is_directory=True)
        self.run_cli("--keep-staging", error="Symlink")
        self.assertEqual(sentinel.read_text(), "keep")

    def test_own_staging_directory_symlink_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        parent = self.root / ".skill-package-staging"
        parent.mkdir()
        (parent / SKILL_NAME).symlink_to(outside, target_is_directory=True)
        self.run_cli("--keep-staging", error="Symlink")
        self.assertEqual(list(outside.iterdir()), [])

    def test_archive_reproducible_across_source_metadata_changes(self) -> None:
        doc = self.write_skill("references/guide.md", "# Guide\n")
        self.run_cli("--zip")
        first = self.archive.read_bytes()
        os.utime(doc, (1700000000, 1700000000))
        doc.chmod(0o755)
        self.run_cli("--zip")
        self.assertEqual(first, self.archive.read_bytes())

    def test_failed_validation_leaves_existing_outputs_intact(self) -> None:
        self.archive.write_bytes(b"old archive")
        sentinel = self.write(f".skill-package-staging/{SKILL_NAME}/keep.txt", "keep")
        self.write("VERSION", "invalid")
        self.run_cli("--zip", "--keep-staging", error="VERSION")
        self.assertEqual(self.archive.read_bytes(), b"old archive")
        self.assertEqual(sentinel.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
