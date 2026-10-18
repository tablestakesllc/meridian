#!/usr/bin/env python3
"""Build the Meridian seed bundle and manifest for a release.

The bundle is the contents of ``templates/``, whose paths mirror the target
repository root. Output (``dist/``):

    meridian-seed-<version>.tar.gz   the bundle, with agent_docs/meridian-manifest.json inside
    manifest.json                    identical copy of the manifest, for inspection

``<version>`` is ``meta.meridian_version`` in templates/agent_docs/weights.default.yaml.

The three core skills are also published as Appendices A, B and D of BOOTSTRAP.md.
The build fails if a skill template and its appendix differ. ``--sync-skills``
rewrites the skill templates from the appendices.

Usage:
    python scripts/build_seed_bundle.py              # check, then build into dist/
    python scripts/build_seed_bundle.py --check      # checks only, no output
    python scripts/build_seed_bundle.py --sync-skills
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import tarfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
BOOTSTRAP = ROOT / "BOOTSTRAP.md"
DIST = ROOT / "dist"
MANIFEST_PATH = "agent_docs/meridian-manifest.json"
CONTRACT_VERSION = 1

# Every bundled file and its manifest kind (Latitude <-> Meridian contract §10).
# machine: used verbatim; Latitude verifies its hash after install.
# knowledge: a template the agent customizes (meridian:fill markers).
FILES: dict[str, str] = {
    ".agents/skills/meridian-v4/weight_memory.py": "machine",
    ".agents/skills/meridian-v4/REBUILD_SPEC.md": "machine",
    ".agents/skills/meridian-v4/SKILL.md": "machine",
    ".agents/skills/meridian-skill-manager/SKILL.md": "machine",
    ".agents/skills/meridian-compaction/SKILL.md": "machine",
    ".gitattributes.meridian": "machine",
    ".gitconfig": "machine",
    ".gitignore.meridian": "machine",
    "agent_docs/SESSION_INIT.md": "knowledge",
    "agent_docs/SESSION_END.md": "knowledge",
    "agent_docs/MEMORY.md": "knowledge",
    "agent_docs/MEMORY_INDEX.yaml": "knowledge",
    "agent_docs/weights.default.yaml": "knowledge",
    "agent_docs/PROMPT_LOG.md": "knowledge",
    "CLAUDE.md": "knowledge",
    ".clinerules/latitude.md": "knowledge",
}

APPENDIX_SKILLS = {
    "A": ".agents/skills/meridian-v4/SKILL.md",
    "B": ".agents/skills/meridian-skill-manager/SKILL.md",
    "C": ".agents/skills/meridian-v4/REBUILD_SPEC.md",
    "D": ".agents/skills/meridian-compaction/SKILL.md",
}

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
FILL_OPEN_RE = re.compile(r'^\s*(?:<!--|#) meridian:fill id="([^"]+)"')
FILL_CLOSE_RE = re.compile(r"^\s*(?:<!--|#) /meridian:fill")


def extract_appendix(bootstrap: str, letter: str) -> str:
    """Return the file published in BOOTSTRAP.md Appendix ``letter``.

    Three layouts exist, all introduced by a ``> Copy the following ...`` note:
    the whole file inside one ```yaml fence; only the frontmatter fenced, with
    the body following as plain markdown; or plain markdown with no fence. Plain
    bodies run to the ``---`` rule before the next appendix (or the Upgrade Log).
    """
    lines = bootstrap.splitlines()
    head = next(i for i, ln in enumerate(lines) if ln.startswith(f"## Appendix {letter}:"))
    first = next(i for i in range(head + 1, len(lines)) if lines[i].strip() and not lines[i].startswith(">"))
    nxt = next(
        i for i in range(first, len(lines))
        if lines[i].startswith("## Appendix ") or lines[i].startswith("## Upgrade Log")
    )

    def plain(a: int) -> list[str]:
        body = lines[a:nxt]
        while body and not body[-1].strip():
            body.pop()
        if body and body[-1].strip() == "---":
            body.pop()
        while body and not body[-1].strip():
            body.pop()
        return body

    if lines[first].strip() != "```yaml":
        return "\n".join(plain(first)) + "\n"
    end = next(i for i in range(first + 1, len(lines)) if lines[i].strip() == "```")
    fenced = lines[first + 1 : end]
    # Frontmatter only: "---", fields, "---".
    closing = [i for i, ln in enumerate(fenced) if ln.strip() == "---"]
    if len(closing) >= 2 and all(not ln.strip() for ln in fenced[closing[1] + 1 :]):
        return "\n".join(fenced[: closing[1] + 1] + plain(end + 1)) + "\n"
    return "\n".join(fenced) + "\n"


def meridian_version() -> str:
    meta = yaml.safe_load((TEMPLATES / "agent_docs/weights.default.yaml").read_text())["meta"]
    return str(meta["meridian_version"])


def check() -> list[str]:
    """Return a list of problems; empty means the templates are releasable."""
    problems: list[str] = []
    for rel in FILES:
        if not (TEMPLATES / rel).is_file():
            problems.append(f"missing template: templates/{rel}")
    on_disk = {
        p.relative_to(TEMPLATES).as_posix()
        for p in TEMPLATES.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    for rel in sorted(on_disk - set(FILES)):
        problems.append(f"unlisted file in templates/: {rel} (add it to FILES or remove it)")
    if problems:
        return problems

    meta = yaml.safe_load((TEMPLATES / "agent_docs/weights.default.yaml").read_text())["meta"]
    version = str(meta.get("meridian_version", ""))
    if not VERSION_RE.match(version):
        problems.append(f"meta.meridian_version must be X.Y.Z, got {version!r}")
    if meta.get("contract_version") != CONTRACT_VERSION:
        problems.append(f"meta.contract_version must be {CONTRACT_VERSION}, got {meta.get('contract_version')!r}")
    if "l1" not in (meta.get("thresholds") or {}):
        problems.append("meta.thresholds.l1 missing")

    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    for letter, rel in APPENDIX_SKILLS.items():
        if (TEMPLATES / rel).read_text(encoding="utf-8") != extract_appendix(bootstrap, letter):
            problems.append(f"templates/{rel} differs from BOOTSTRAP.md Appendix {letter} (run --sync-skills)")

    for rel, kind in FILES.items():
        text = (TEMPLATES / rel).read_text(encoding="utf-8")
        depth, ids = 0, []
        for n, ln in enumerate(text.splitlines(), 1):
            if m := FILL_OPEN_RE.match(ln):
                if depth:
                    problems.append(f"templates/{rel}:{n}: nested meridian:fill")
                depth += 1
                ids.append(m.group(1))
            elif FILL_CLOSE_RE.match(ln):
                depth -= 1
        if depth:
            problems.append(f"templates/{rel}: unclosed meridian:fill")
        if len(ids) != len(set(ids)):
            problems.append(f"templates/{rel}: duplicate meridian:fill id")
        if kind == "machine" and ids:
            problems.append(f"templates/{rel}: machine file must not carry meridian:fill markers")

    session_init = (TEMPLATES / "agent_docs/SESSION_INIT.md").read_text(encoding="utf-8")
    for needle in ("## Current State", "HALT", "## File Map", "| File | Role | Committed? |"):
        if needle not in session_init:
            problems.append(f"SESSION_INIT.md template lacks {needle!r}")
    if not re.search(r"^## §0(\D|$)", (TEMPLATES / "agent_docs/MEMORY.md").read_text(), re.M):
        problems.append("MEMORY.md template lacks a '## §0' heading")
    if re.search(r"^## Session: \d", (TEMPLATES / "agent_docs/PROMPT_LOG.md").read_text(), re.M):
        problems.append("PROMPT_LOG.md template contains a real session entry")

    weights = yaml.safe_load((TEMPLATES / "agent_docs/weights.default.yaml").read_text())
    l1 = float(meta["thresholds"]["l1"]) if "thresholds" in meta else 8.0
    if not any(float(b.get("seed_weight", 0)) >= l1 for b in weights.get("blocks") or []):
        problems.append("weights.default.yaml needs a starter block seeded >= thresholds.l1")
    index = yaml.safe_load((TEMPLATES / "agent_docs/MEMORY_INDEX.yaml").read_text())
    if not index.get("blocks"):
        problems.append("MEMORY_INDEX.yaml needs at least one starter block")
    return problems


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(version: str) -> dict:
    return {
        "meridian_version": version,
        "contract_version": CONTRACT_VERSION,
        "files": [
            {"path": rel, "sha256": sha256((TEMPLATES / rel).read_bytes()), "kind": kind}
            for rel, kind in FILES.items()
        ],
    }


def build() -> tuple[Path, Path]:
    version = meridian_version()
    data = manifest(version)
    manifest_bytes = (json.dumps(data, indent=2) + "\n").encode()

    def add(tar: tarfile.TarFile, name: str, payload: bytes) -> None:
        info = tarfile.TarInfo(name)
        info.size = len(payload)
        info.mtime = 0
        info.mode = 0o755 if name.endswith(".py") else 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        tar.addfile(info, io.BytesIO(payload))

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for rel in sorted(FILES):
            add(tar, rel, (TEMPLATES / rel).read_bytes())
        add(tar, MANIFEST_PATH, manifest_bytes)

    DIST.mkdir(exist_ok=True)
    bundle = DIST / f"meridian-seed-{version}.tar.gz"
    with bundle.open("wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
        gz.write(raw.getvalue())
    manifest_out = DIST / "manifest.json"
    manifest_out.write_bytes(manifest_bytes)
    return bundle, manifest_out


def sync_skills() -> None:
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    for letter, rel in APPENDIX_SKILLS.items():
        target = TEMPLATES / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(extract_appendix(bootstrap, letter), encoding="utf-8")
        print(f"wrote templates/{rel} from Appendix {letter}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="run checks only")
    group.add_argument("--sync-skills", action="store_true", help="rewrite skill templates from BOOTSTRAP.md")
    args = parser.parse_args(argv)

    if args.sync_skills:
        sync_skills()
        return 0
    problems = check()
    for p in problems:
        print(f"ERROR: {p}", file=sys.stderr)
    if problems:
        return 1
    if args.check:
        print(f"OK: templates releasable as {meridian_version()}")
        return 0
    bundle, manifest_out = build()
    print(f"built {bundle.relative_to(ROOT)} ({bundle.stat().st_size} bytes)")
    print(f"      {manifest_out.relative_to(ROOT)}")
    print(f"sha256 {sha256(bundle.read_bytes())}  {bundle.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
