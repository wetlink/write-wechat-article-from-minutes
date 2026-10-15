#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


SKILL_NAME = "write-wechat-article-from-minutes"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NUMBER = r"(?:0|[1-9][0-9]*)"
PRERELEASE = rf"(?:{NUMBER}|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
VERSION_RE = re.compile(
    rf"{NUMBER}\.{NUMBER}\.{NUMBER}(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
DESTINATION = r"(<[^>\n]+>|(?:\\.|[^\s()\\]|\([^()\n]*\))+)"
LINK_RE = re.compile(
    r"\[(?:\\.|[^\]\\])*\]\(\s*" + DESTINATION + r"(?:\s+[\"'][^\n]*?[\"'])?\s*\)"
)
REFERENCE_RE = re.compile(r"^ {0,3}\[[^\]\n]+\]:\s*" + DESTINATION, re.MULTILINE)


class ValidationError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate and package this Skill.")
    parser.add_argument("--source-root", type=Path, default=root)
    parser.add_argument("--keep-staging", action="store_true")
    parser.add_argument("--zip", action="store_true")
    return parser.parse_args()


def parse_string_fields(text: str, context: str) -> dict[str, str]:
    """Read the flat string mappings used here, not arbitrary YAML objects."""
    data: dict[str, str] = {}
    lines = text.splitlines()
    indent = min(
        (len(line) - len(line.lstrip(" ")) for line in lines
         if line.strip() and not line.lstrip().startswith("#")), default=0,
    )
    lines = [line[indent:] if line.startswith(" " * indent) else line for line in lines]
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
        if not match:
            raise ValidationError(f"Invalid {context} field: {line}")
        key, raw = match.groups()
        if key in data:
            raise ValidationError(f"Duplicate {context} field: {key}")
        value = re.sub(r"\s+#.*$", "", raw).strip()
        if re.fullmatch(r"[|>][-+]?", value):
            block = []
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith(" ")):
                block.append(lines[index])
                index += 1
            content = textwrap.dedent("\n".join(block)).rstrip("\n")
            if value.startswith(">"):
                content = re.sub(r"(?<=\S)\n(?=\S)", " ", content)
            value = content + ("" if value.endswith("-") else "\n")
        elif raw.startswith('"'):
            try:
                value, end = json.JSONDecoder().raw_decode(raw)
            except ValueError as exc:
                raise ValidationError(f"Invalid {context} string: {key}") from exc
            if raw[end:].strip() and not raw[end:].lstrip().startswith("#"):
                raise ValidationError(f"Invalid {context} string: {key}")
        elif raw.startswith("'"):
            quoted = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", raw)
            if not quoted:
                raise ValidationError(f"Invalid {context} string: {key}")
            value = quoted[1].replace("''", "'")
        elif (value.startswith(("[", "{", "&", "*", "!", "#"))
              or value.lower() in {"null", "~", "true", "false", "yes", "no", "on", "off"}
              or re.fullmatch(r"[-+]?[0-9]+(?:\.[0-9]+)?", value)):
            raise ValidationError(f"{context} {key} must be a string.")
        data[key] = value
    return data


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        raise ValidationError(f"{path} must start with closed YAML frontmatter.")
    data = parse_string_fields(match[1], "frontmatter")
    if set(data) != {"name", "description"}:
        raise ValidationError("Frontmatter must contain only name and description.")
    return data, text[match.end():]


def reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise ValidationError(f"Symlink not allowed: {path}")


def require_file(path: Path) -> None:
    reject_symlink(path)
    if not path.is_file():
        raise ValidationError(f"Required file not found: {path}")


def copy_package(source_root: Path, staging_root: Path) -> Path:
    source_skill_dir = source_root / "skill" / SKILL_NAME
    for path in (source_root, source_root / "skill", source_skill_dir):
        reject_symlink(path)
    sources = {
        "SKILL.md": source_skill_dir / "SKILL.md",
        "agents/openai.yaml": source_skill_dir / "agents" / "openai.yaml",
        "VERSION": source_root / "VERSION",
        "LICENSE": source_root / "LICENSE",
    }

    def collect(directory: Path) -> None:
        for path in sorted(directory.iterdir()):
            reject_symlink(path)
            relative = path.relative_to(source_skill_dir)
            rel = relative.as_posix()
            docs = relative.parts[0] in {"references", "examples"}
            visible = not any(part.startswith(".") for part in relative.parts)
            if path.is_dir() and (rel == "agents" or (docs and visible)):
                collect(path)
            elif path.is_file() and rel == f"{SKILL_NAME}.zip":
                continue
            elif path.is_file() and (rel in {"SKILL.md", "agents/openai.yaml"}
                                     or (docs and visible and path.suffix == ".md")):
                sources[rel] = path
            else:
                raise ValidationError(f"Unexpected package entry: {path}")

    require_file(source_skill_dir / "SKILL.md")
    collect(source_skill_dir)
    for src in sources.values():
        require_file(src)
    package_dir = staging_root / SKILL_NAME
    for rel, src in sources.items():
        dst = package_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return package_dir


def validate_skill(package_dir: Path) -> None:
    data, _ = parse_frontmatter(package_dir / "SKILL.md")
    if data["name"] != SKILL_NAME:
        raise ValidationError(f"Skill name must be {SKILL_NAME}.")
    if not NAME_RE.fullmatch(data["name"]):
        raise ValidationError("Skill name must be lowercase hyphen-case.")
    if not data["description"].strip() or len(data["description"]) > 1024:
        raise ValidationError("Skill description must be nonempty and at most 1024 characters.")


def validate_version(package_dir: Path) -> None:
    version = (package_dir / "VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_RE.fullmatch(version):
        raise ValidationError(f"VERSION must be a semantic version, got {version!r}.")
    if not (package_dir / "LICENSE").read_text(encoding="utf-8").strip():
        raise ValidationError("LICENSE must not be empty.")


def validate_agents(package_dir: Path) -> None:
    text = (package_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
    lines = text.splitlines()
    interfaces = [index for index, line in enumerate(lines) if line.startswith("interface:")]
    if len(interfaces) != 1:
        raise ValidationError("agents/openai.yaml must contain one interface mapping.")
    start = interfaces[0]
    if not re.fullmatch(r"interface:[ \t]*(?:#.*)?", lines[start]):
        raise ValidationError("agents/openai.yaml interface must be a mapping.")
    block = []
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith((" ", "#")):
            break
        block.append(line)
    data = parse_string_fields("\n".join(block), "agents/openai.yaml interface")
    for key in ("display_name", "short_description", "default_prompt"):
        if not data.get(key, "").strip():
            raise ValidationError(f"agents/openai.yaml requires nonempty {key}.")
    if not re.search(rf"\${re.escape(SKILL_NAME)}(?![\w-])", data["default_prompt"]):
        raise ValidationError(f"default_prompt must invoke ${SKILL_NAME}.")


def markdown_prose(text: str) -> str:
    lines = []
    fence = ""
    for line in text.splitlines(keepends=True):
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", line):
                fence = ""
            lines.append("\n")
        else:
            match = re.match(r" {0,3}(`{3,}|~{3,})", line)
            if match:
                fence = match[1]
                lines.append("\n")
            else:
                lines.append(line)
    text = re.sub(r"<!--.*?-->", "", "".join(lines), flags=re.DOTALL)
    # Match equal backtick runs, including multi-backtick inline examples.
    return re.sub(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)", "", text, flags=re.DOTALL)


def validate_links(package_dir: Path) -> None:
    root = package_dir.resolve()
    for path in sorted(package_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if path.name == "SKILL.md" and path.parent == package_dir:
            _, text = parse_frontmatter(path)
        prose = markdown_prose(text)
        for match in list(LINK_RE.finditer(prose)) + list(REFERENCE_RE.finditer(prose)):
            target = re.sub(r"\\(.)", r"\1", match[1].strip("<>"))
            try:
                url = urlsplit(target)
            except ValueError as exc:
                raise ValidationError(f"Invalid link in {path}: {target}") from exc
            if (url.scheme and url.scheme != "file") or target.startswith("//"):
                continue
            destination = (path.parent / unquote(url.path)).resolve()
            if url.scheme == "file" or not destination.is_relative_to(root):
                raise ValidationError(f"Link outside package in {path}: {target}")
            if url.path and not destination.is_file():
                raise ValidationError(f"Missing local file in {path}: {target}")


def write_zip(package_dir: Path, zip_path: Path) -> None:
    reject_symlink(zip_path)
    files = sorted(path for path in package_dir.rglob("*") if path.is_file())
    if zip_path.resolve().is_relative_to(package_dir.resolve()):
        raise ValidationError("Archive output must be outside the staged package.")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".skill-zip-", dir=zip_path.parent) as tmp:
        pending = Path(tmp) / "package.zip"
        with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                require_file(path)
                info = zipfile.ZipInfo(path.relative_to(package_dir.parent).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, path.read_bytes())
        with zipfile.ZipFile(pending) as zf:
            bad = zf.testzip()
        if bad:
            raise ValidationError(f"Zip integrity check failed at {bad}")
        pending.replace(zip_path)


def main() -> int:
    args = parse_args()
    try:
        reject_symlink(args.source_root)
        source_root = args.source_root.resolve()
        with tempfile.TemporaryDirectory(prefix=f"{SKILL_NAME}.") as tmp:
            package_dir = copy_package(source_root, Path(tmp))
            validate_version(package_dir)
            validate_skill(package_dir)
            validate_agents(package_dir)
            validate_links(package_dir)
            if args.keep_staging:
                kept_parent = source_root / ".skill-package-staging"
                kept_dir = kept_parent / SKILL_NAME
                reject_symlink(kept_parent)
                reject_symlink(kept_dir)
                kept_parent.mkdir(parents=True, exist_ok=True)
                if kept_dir.exists():
                    shutil.rmtree(kept_dir)
                shutil.copytree(package_dir, kept_dir)
                print(f"[ok] kept staged package: {kept_dir}")
            if args.zip:
                zip_path = source_root / "skill" / SKILL_NAME / f"{SKILL_NAME}.zip"
                write_zip(package_dir, zip_path)
                print(f"[ok] wrote zip: {zip_path}")
        print(f"[ok] {SKILL_NAME} skill package validated")
        return 0
    except (ValidationError, OSError, UnicodeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
