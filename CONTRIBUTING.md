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
`tablestakesllc/meridian_dev_memory`. Without access, that clone fails with an
authentication error on `agent_docs/`. The public files are unaffected.

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

`.agents/skills` and `.claude` are not committed. They are gitignored symlinks
into the submodule, so agents find the maintainers' skills and settings at the
standard paths:

| Path | Points to |
|---|---|
| `.agents/skills` | `agent_docs/.agents/skills` |
| `.claude` | `agent_docs/.claude` (its `skills` link points to `../.agents/skills` inside the submodule) |

Linux, macOS, WSL:

```bash
mkdir -p .agents
ln -s ../agent_docs/.agents/skills .agents/skills
ln -s agent_docs/.claude .claude
```

Windows (PowerShell, Developer Mode on or an elevated prompt):

```powershell
git config --global core.symlinks true   # before cloning, so the submodule's own .claude/skills link is created
New-Item -ItemType Directory -Force .agents | Out-Null
New-Item -ItemType SymbolicLink -Path .agents\skills -Target ..\agent_docs\.agents\skills
New-Item -ItemType SymbolicLink -Path .claude -Target agent_docs\.claude
```

Check: `ls .agents/skills/` and `ls .claude/skills/` list the same skills.

The `.gitignore` entries are `.agents` and `.claude` with no trailing slash. A
trailing slash only matches directories and would not ignore a symlink.

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

## Public Repo Changes

Changes to the public files go through a branch and a pull request to `main`.
Never copy maintainer memory (anything under `agent_docs/`) into public files.
