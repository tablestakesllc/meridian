# Contributing to Meridian

Meridian is developed with Meridian. The maintainers' own memory for this repo
(session log, memory blocks, skills, agent settings) lives in a **private**
submodule mounted at `agent_docs/`. Everything else in this repo is public.

You do **not** need the submodule to contribute. Clone normally, work on the
public files, and open a pull request.

```bash
git clone https://github.com/tablestakesllc/meridian.git
```

Do not use `--recurse-submodules` unless you have access to
`tablestakesllc/meridian-dev-memory`. Without access, that clone fails with an
authentication error on `agent_docs/`. The public files are unaffected.

### Tests

```bash
pip install pyyaml pytest
python -m pytest tests/ -q
python scripts/build_seed_bundle.py --check
```

### Seed bundle templates

`templates/` is the seed bundle: its paths mirror a target repository root.

- **Core files** (`kind: machine` in the manifest) ship verbatim and must be identical
  in every installation. The three core skills and `REBUILD_SPEC.md` are generated from
  `BOOTSTRAP.md` Appendices A–D: edit the appendix, then run
  `python scripts/build_seed_bundle.py --sync-skills`. The build fails if they drift.
- **Knowledge files** are templates. Every part the installing agent must write is
  wrapped in a `meridian:fill` marker (`<!-- meridian:fill id="..." -->` …
  `<!-- /meridian:fill -->`, or `# meridian:fill id="..."` … `# /meridian:fill` in
  YAML). Markers never nest and carry an instruction, never real content.
- Every file in `templates/` must be listed in `FILES` in
  `scripts/build_seed_bundle.py`.

---

## Releases

Meridian uses SemVer with three-part tags (`vX.Y.Z`) from 4.7.0 on.

1. Set `meta.meridian_version` in `templates/agent_docs/weights.default.yaml`, add an
   Upgrade Log entry to `BOOTSTRAP.md`, and add a row to the README versions table.
2. If the release makes a change the Latitude ↔ Meridian contract lists as
   **Breaking**, bump `meta.contract_version` there and `CONTRACT_VERSION` in
   `scripts/build_seed_bundle.py`, and update the contract's compatibility matrix in
   the Latitude repo in the same release. Otherwise leave both unchanged.
3. Run the tests, then build:
   ```bash
   python scripts/build_seed_bundle.py
   ```
   This writes `dist/meridian-seed-<version>.tar.gz` and `dist/manifest.json` and prints
   the bundle's SHA-256. The build is reproducible: the same templates give the same bytes.
4. Maintainers run the release guard on the tree and the bundle (see below).
5. Merge the release PR, tag `vX.Y.Z` on `main`, and attach both files to the GitHub
   release:
   ```bash
   gh release create vX.Y.Z dist/meridian-seed-X.Y.Z.tar.gz dist/manifest.json \
     --title "vX.Y.Z" --notes "<public summary>"
   ```
6. Give Latitude the new version and the bundle SHA-256 if it should pin this release.

Every release ships a bundle and manifest. A release without them is incomplete.

---

## Maintainer Setup

Maintainers with access to the private submodule run this once per clone.

### 1. Clone with the submodule

```bash
git clone --recurse-submodules https://github.com/tablestakesllc/meridian.git
cd meridian
git -C agent_docs switch main    # submodules check out detached; edit on a branch
```

Already cloned without it:

```bash
git submodule update --init
git -C agent_docs switch main
```

### 2. Git settings

```bash
git config push.recurseSubmodules check      # refuse a parent push that points at an unpushed submodule commit
git config status.submoduleSummary true      # show unrecorded submodule commits in git status
git config submodule.agent_docs.update rebase
```

### 3. Create the local symlinks

`.agents/skills`, `.claude` and `CLAUDE.md` are not committed. They are
gitignored symlinks into the submodule, so agents find the maintainers' skills,
settings and bootstrap pointer at the standard paths:

| Path | Points to |
|---|---|
| `.agents/skills` | `agent_docs/.agents/skills` |
| `.claude` | `agent_docs/.claude` (its `skills` link points to `../.agents/skills` inside the submodule) |
| `CLAUDE.md` | `agent_docs/CLAUDE.md` |

Linux, macOS, WSL:

```bash
mkdir -p .agents
ln -s ../agent_docs/.agents/skills .agents/skills
ln -s agent_docs/.claude .claude
ln -s agent_docs/CLAUDE.md CLAUDE.md
```

Windows (PowerShell, Developer Mode on or an elevated prompt):

```powershell
git config --global core.symlinks true   # before cloning, so the submodule's own .claude/skills link is created
New-Item -ItemType Directory -Force .agents | Out-Null
New-Item -ItemType SymbolicLink -Path .agents\skills -Target ..\agent_docs\.agents\skills
New-Item -ItemType SymbolicLink -Path .claude -Target agent_docs\.claude
New-Item -ItemType SymbolicLink -Path CLAUDE.md -Target agent_docs\CLAUDE.md
```

Check: `ls .agents/skills/` and `ls .claude/skills/` list the same skills, and
`head -1 CLAUDE.md` prints the maintainer instructions heading.

The `.gitignore` entries are `/.agents`, `/.claude` and `/CLAUDE.md`: anchored
to the root, with no trailing slash. A trailing slash only matches directories
and would not ignore a symlink.

### 4. First session

Start an agent session at the repo root. The agent follows
`agent_docs/SESSION_INIT.md`, which seeds the per-developer weights on first
run. If the weight script's `--seed` creates `.gitconfig` or `.gitattributes`
at the repo root, they are ignored here and must not be committed.

---

## Working in the Submodule

The submodule is version control and backup for maintainer memory. It does
**not** follow the public repo's branch rules: commit directly to `main`.

The public repo records which submodule commit it uses. A memory change is
therefore two commits, pushed in this order:

```bash
git -C agent_docs add -A
git -C agent_docs commit -m "docs: ..."
git -C agent_docs push            # 1. submodule first

git add agent_docs                # 2. record the new submodule commit
git commit -m "chore: bump agent_docs"
git push                          # 3. then the parent
```

If the parent is pushed first, it points at a commit nobody else can fetch.
`push.recurseSubmodules check` blocks that.

Bump the pointer at session end, not after every memory edit, to keep the
public history clean. Until then the parent shows `agent_docs` as modified,
which is harmless.

Merge drivers are per repository. The submodule carries its own
`.gitattributes` with `merge=union` for `PROMPT_LOG.md`, `MEMORY.md`,
`MEMORY_INDEX.yaml`, `weights.default.yaml` and skill files.

---

## Public Repo Changes and Releases

Changes to the public files go through a branch and a pull request to `main`.

Maintainer memory never enters the public repo or a release. That covers
everything under `agent_docs/`: memory, skills, session logs, development notes
and tooling. Concretely:

- Public docs and release templates are written fresh, never copied from `agent_docs/`.
- Public commit messages, PRs, issues, tags and release notes describe the public
  change only.
- Stage named files in the public repo; never `git add -A`.
- Before every public commit, push, tag or release, maintainers run
  `agent_docs/tools/release_guard.sh` (and `release_guard.sh <bundle>` for a
  release bundle). It must print `release_guard: OK`.
