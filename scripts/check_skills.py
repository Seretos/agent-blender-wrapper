#!/usr/bin/env python3
"""Validate every skills/*/SKILL.md in this repo.

Generalizes the old hardcoded `skills/blender-wrapper/SKILL.md` frontmatter
check in .github/workflows/lint.yml into something that scales to any number
of skills shipped by this plugin. Stdlib only (no PyYAML) so it needs no
extra install step on the CI runner.

For every skills/*/SKILL.md this checks, in order:
  1. YAML frontmatter is present and parseable with a simple regex (matching
     the shape the original inline lint step used).
  2. The frontmatter has both `name:` and `description:` keys.
  3. The frontmatter `name:` value equals the skill's directory name.
  4. Every fenced ```python code block in the file compiles (a syntax smoke
     test on any copy-paste-verbatim snippets, not a behavioural test).
  5. Any required content markers for that skill (see REQUIRED_MARKERS) are
     present in the file.

It also asserts that every directory in REQUIRED_SKILL_DIRS actually exists
under skills/, so a missing skill directory fails loudly instead of the walk
over skills/*/SKILL.md vacuously finding nothing to check.

Exits 1 with a clear message on any failure, 0 when everything passes.
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Skill directories that must exist under skills/. Keeps a missing skill from
# silently passing because the glob below found nothing to check.
REQUIRED_SKILL_DIRS = ["blender-wrapper", "blender-game-export"]

# Per-skill content markers that must appear somewhere in SKILL.md. Proves
# specific identifiers are present (not prose-quality) -- see AGENTS.md.
REQUIRED_MARKERS: dict[str, list[str]] = {
    "blender-game-export": [
        "FBX_SCALE_ALL",
        "bake_space_transform",
        "UnitScaleFactor",
        "mesh_smooth_type",
        "(-bx, bz, -by)",
        "axis-reconciliation-note",
    ],
}

# Marker that must appear specifically inside the frontmatter `description:`
# field (not just anywhere in the file), keyed by skill directory name. Used
# to prove a German-language trigger phrase is wired into the skill trigger,
# not just mentioned somewhere in the body.
REQUIRED_DESCRIPTION_MARKERS: dict[str, list[str]] = {
    "blender-game-export": ["exportier"],
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
PYTHON_FENCE_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)


class CheckError(Exception):
    pass


def check_skill_dirs_exist() -> None:
    missing = [d for d in REQUIRED_SKILL_DIRS if not (SKILLS_DIR / d).is_dir()]
    if missing:
        raise CheckError(
            "Missing required skill director"
            + ("y" if len(missing) == 1 else "ies")
            + ": "
            + ", ".join(missing)
        )


def check_one_skill(skill_md: pathlib.Path) -> None:
    dir_name = skill_md.parent.name
    text = skill_md.read_text(encoding="utf-8")

    m = FRONTMATTER_RE.match(text)
    if not m:
        raise CheckError(f"{skill_md}: missing YAML frontmatter")
    frontmatter = m.group(1)

    if "name:" not in frontmatter or "description:" not in frontmatter:
        raise CheckError(f"{skill_md}: frontmatter missing 'name' or 'description'")

    name_m = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    if not name_m:
        raise CheckError(f"{skill_md}: could not parse 'name:' value from frontmatter")
    name_value = name_m.group(1).strip()
    if name_value != dir_name:
        raise CheckError(
            f"{skill_md}: frontmatter name '{name_value}' != directory name '{dir_name}'"
        )

    for i, block in enumerate(PYTHON_FENCE_RE.findall(text), start=1):
        try:
            compile(block, f"{skill_md}#python-block-{i}", "exec")
        except SyntaxError as e:
            raise CheckError(f"{skill_md}: python code block {i} fails to compile: {e}")

    for marker in REQUIRED_MARKERS.get(dir_name, []):
        if marker not in text:
            raise CheckError(f"{skill_md}: missing required content marker: {marker!r}")

    for marker in REQUIRED_DESCRIPTION_MARKERS.get(dir_name, []):
        if marker not in frontmatter:
            raise CheckError(
                f"{skill_md}: missing required marker in frontmatter description: {marker!r}"
            )

    print(f"{skill_md.relative_to(REPO_ROOT)}: OK")


def main() -> int:
    try:
        check_skill_dirs_exist()

        skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
        if not skill_files:
            raise CheckError(f"No skills/*/SKILL.md files found under {SKILLS_DIR}")

        for skill_md in skill_files:
            check_one_skill(skill_md)
    except CheckError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1

    print(f"All {len(skill_files)} skill(s) OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
