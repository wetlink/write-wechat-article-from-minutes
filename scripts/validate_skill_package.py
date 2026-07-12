#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


SKILL_NAME = "write-wechat-article-from-minutes"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ValidationError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate and package this Skill.")
    parser.add_argument("--source-root", type=Path, default=root)
    parser.add_argument("--keep-staging", action="store_true")
    parser.add_argument("--zip", action="store_true")
    return parser.parse_args()


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValidationError(f"{path} must start with YAML frontmatter.")
    try:
        _, frontmatter, body = text.split("---\n", 2)
    except ValueError as exc:
        raise ValidationError(f"{path} frontmatter is not closed.") from exc
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValidationError(f"Invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    if set(data) != {"name", "description"}:
        raise ValidationError("Frontmatter must contain only name and description.")
    return data, body


def require_file(path: Path) -> None:
    if not path.is_file():
        raise ValidationError(f"Required file not found: {path}")


def copy_package(source_root: Path, staging_root: Path) -> Path:
    source_skill_dir = source_root / "skill" / SKILL_NAME
    sources = {
        "SKILL.md": source_skill_dir / "SKILL.md",
        "agents/openai.yaml": source_skill_dir / "agents" / "openai.yaml",
    }
    for src in sources.values():
        require_file(src)
    package_dir = staging_root / SKILL_NAME
    for rel, src in sources.items():
        dst = package_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return package_dir


def validate_skill(package_dir: Path) -> None:
    data, body = parse_frontmatter(package_dir / "SKILL.md")
    if data["name"] != SKILL_NAME:
        raise ValidationError(f"Skill name must be {SKILL_NAME}.")
    if not NAME_RE.fullmatch(data["name"]):
        raise ValidationError("Skill name must be lowercase hyphen-case.")
    if len(data["description"]) < 80:
        raise ValidationError("Description is too short for reliable discovery.")
    required_phrases = [
        "Feishu/Lark Minutes",
        "WeChat official-account article",
        "public fact-checking",
        "Feishu doc creation",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in data["description"] + body]
    if missing:
        raise ValidationError("SKILL.md missing required phrases: " + ", ".join(missing))


def validate_agents(package_dir: Path) -> None:
    text = (package_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
    required = ["display_name:", "short_description:", "default_prompt:"]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValidationError("agents/openai.yaml missing: " + ", ".join(missing))


def write_zip(package_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name == ".DS_Store" or path.suffix == ".zip":
                continue
            zf.write(path, path.relative_to(package_dir.parent))
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
    if bad:
        raise ValidationError(f"Zip integrity check failed at {bad}")


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    try:
        with tempfile.TemporaryDirectory(prefix=f"{SKILL_NAME}.") as tmp:
            package_dir = copy_package(source_root, Path(tmp))
            validate_skill(package_dir)
            validate_agents(package_dir)
            if args.keep_staging:
                kept_parent = source_root / ".skill-package-staging"
                kept_dir = kept_parent / SKILL_NAME
                if kept_parent.exists():
                    shutil.rmtree(kept_parent)
                kept_parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(package_dir, kept_dir)
                print(f"[ok] kept staged package: {kept_dir}")
            if args.zip:
                zip_path = source_root / "skill" / SKILL_NAME / f"{SKILL_NAME}.zip"
                write_zip(package_dir, zip_path)
                print(f"[ok] wrote zip: {zip_path}")
        print(f"[ok] {SKILL_NAME} skill package validated")
        return 0
    except ValidationError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
