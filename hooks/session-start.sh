#!/bin/bash
# Lane OS SessionStart hook.
# Locate the spine repo, pull it, refresh user-level CLAUDE.md, symlink skills,
# pull the current code repo if we are in one, then emit a COMPACT read-directive
# that points the session at the right files for its lane.
#
# Portable: set LANE_OS_ROOT to your spine repo path, or rely on auto-detection.

# --- locate the spine repo ---------------------------------------------------
SPINE=""
if [ -n "$LANE_OS_ROOT" ] && [ -d "$LANE_OS_ROOT/.git" ]; then
  SPINE="$LANE_OS_ROOT"
else
  for candidate in \
    "$HOME/work/spine" \
    "$HOME/repos/spine" \
    "$HOME/lane-os" \
    "$HOME/repos/lane-os"; do
    if [ -d "$candidate/.git" ]; then SPINE="$candidate"; break; fi
  done
fi
# Nothing to inject on this machine.
[ -z "$SPINE" ] && exit 0

# --- pull spine (ff-only, quiet, non-blocking) -------------------------------
SPINE_PULL_FAILED=0
(cd "$SPINE" && git pull --ff-only --quiet 2>/dev/null) || SPINE_PULL_FAILED=1

# --- refresh user-level CLAUDE.md from the constitution -----------------------
if [ -f "$SPINE/global/CLAUDE.md" ]; then
  mkdir -p "$HOME/.claude"
  # Only copy if it is NOT already a symlink (copying would clobber the link).
  if [ ! -L "$HOME/.claude/CLAUDE.md" ]; then
    cp "$SPINE/global/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
  fi
fi

# --- sync skills as symlinks (never copies) ----------------------------------
if [ -d "$SPINE/skills" ]; then
  mkdir -p "$HOME/.claude/skills"
  for skill_dir in "$SPINE/skills"/*/; do
    [ -d "$skill_dir" ] || continue
    name=$(basename "$skill_dir")
    link="$HOME/.claude/skills/$name"
    if [ -e "$link" ] && [ ! -L "$link" ]; then rm -rf "$link"; fi
    ln -sfn "${skill_dir%/}" "$link" 2>/dev/null || true
  done
  # prune links whose target was deleted (retired skills)
  for link in "$HOME/.claude/skills"/*; do
    [ -L "$link" ] || continue
    case "$(readlink "$link")" in
      "$SPINE/skills/"*) [ -e "$link" ] || rm -f "$link" ;;
    esac
  done
fi

# --- detect the lane ---------------------------------------------------------
IS_CODE_LANE=0; CODE_NAME=""; CODE_PULL_FAILED=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  top=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ "$top" != "$SPINE" ] && [ -n "$top" ]; then
    git pull --ff-only --quiet 2>/dev/null || CODE_PULL_FAILED=1
    IS_CODE_LANE=1
    CODE_NAME=$(basename "$top")
  fi
fi

IS_DESK=0; DESK_NAME=""
if [ "$IS_CODE_LANE" = "0" ]; then
  cwd_real="$(pwd -P 2>/dev/null)"
  spine_real="$(cd "$SPINE" && pwd -P 2>/dev/null)"
  case "$cwd_real/" in
    "$spine_real/desks/"*)
      rest="${cwd_real#"$spine_real"/desks/}"
      DESK_NAME="${rest%%/*}"
      [ -n "$DESK_NAME" ] && IS_DESK=1
      ;;
  esac
fi

# --- emit the compact, lane-aware read-directive -----------------------------
if [ "$IS_CODE_LANE" = "1" ] && [ -n "$CODE_NAME" ]; then
  PDIR="$SPINE/projects/$CODE_NAME"
  cat <<RULE
=== CODE LANE: ${CODE_NAME} (cwd is the ${CODE_NAME} repo, NOT the spine) ===

WRITE LANE: write only under this repo and ${SPINE}/projects/${CODE_NAME}/ and ${SPINE}/brain/drafts/.
FORBIDDEN even if asked: writing ${SPINE}/brain/ (except drafts/), /memory/, /global/, /skills/, or any other projects/<name>/. Decline before the write and redirect: open a spine session, or stage in brain/drafts/.

=== READ NOW (blocking): Read every file below before your first reply. ===
The index files are tables of contents, not substitutes. Treat these as ground truth over assumptions.
  - ${SPINE}/brain/ACTIVE_NOW.md   (cross-cutting priorities)
RULE
  [ -f "$PDIR/STATUS.md" ] && echo "  - $PDIR/STATUS.md   (THIS lane's live state)"
  [ -f "$PDIR/MEMORY.md" ] && echo "  - $PDIR/MEMORY.md   (THIS lane's durable facts)"
  [ "$SPINE_PULL_FAILED" = "1" ] && echo "NOTE: spine pull FAILED; files may be stale."
  [ "$CODE_PULL_FAILED" = "1" ] && echo "NOTE: code repo pull FAILED; files may be stale."
  echo "=== END SESSION CONTEXT ==="
elif [ "$IS_DESK" = "1" ] && [ -n "$DESK_NAME" ]; then
  DDIR="$SPINE/desks/$DESK_NAME"
  cat <<RULE
=== DESK: ${DESK_NAME} (cwd is desks/${DESK_NAME}, a TOPIC lane) ===

WRITE LANE: write only under ${DDIR}/ and ${SPINE}/brain/drafts/.
FORBIDDEN even if asked: writing ${SPINE}/brain/ (except drafts/), /memory/, /global/, /skills/, any other desk, or any code repo. Stage cross-cutting facts in brain/drafts/, or open the right lane.

=== READ NOW (blocking): Read every file below before your first reply. ===
Read your desk's OWN CLAUDE.md FIRST: it names your context slice + posture. Do NOT load the whole brain; a desk reads its slice.
  - ${DDIR}/CLAUDE.md   (this desk's contract)
RULE
  [ -f "$DDIR/LOG.md" ] && echo "  - $DDIR/LOG.md   (this desk's running record)"
  [ "$SPINE_PULL_FAILED" = "1" ] && echo "NOTE: spine pull FAILED; files may be stale."
  echo "=== END SESSION CONTEXT ==="
else
  cat <<RULE
=== SPINE SESSION (workspace-root) ===

=== READ NOW (blocking): Read every file below before your first reply. ===
The index files are tables of contents, not substitutes. Treat these as ground truth over assumptions.
  - ${SPINE}/brain/ACTIVE_NOW.md   (cross-cutting priorities)
  - ${SPINE}/brain/CONCERNS.md     (open loops and worries)
On demand: ${SPINE}/brain/ WHO_I_AM.md, PEOPLE.md, DECISIONS.md, WEEKLY_LOG.md
RULE
  draft_count=$(find "$SPINE/brain/drafts" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  if [ "${draft_count:-0}" -gt 0 ]; then
    echo "NOTE: brain/drafts/ holds ${draft_count} staged file(s) awaiting merge."
  fi
  [ "$SPINE_PULL_FAILED" = "1" ] && echo "NOTE: spine pull FAILED; files may be stale."
  echo "=== END SESSION CONTEXT ==="
fi

# --- cross-lane awareness: refresh the local switchboard cache (best-effort) --
( python3 "$SPINE/scripts/build-switchboard.py" >/dev/null 2>&1 & ) 2>/dev/null

exit 0
