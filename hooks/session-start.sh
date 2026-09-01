#!/bin/bash
# Lane OS SessionStart hook.
# Locate the spine repo, pull it, refresh user-level CLAUDE.md, symlink skills,
# pull the current code repo if we are in one, then emit a COMPACT read-directive
# that points the session at the right files for its lane.
#
# Pointers, not file dumps: hook stdout is truncated to a small inline preview when it
# is large, and anything past that lands in a file the model does not auto-read. So
# this prints the PATHS to read and instructs the session to Read them itself.
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
SPINE="$(cd "$SPINE" && pwd -P)"

# --- pull spine (ff-only, quiet, non-blocking) -------------------------------
# pull_state says WHY a pull failed (diverged vs offline) instead of a bare FAILED.
pull_state() (
  cd "$1" 2>/dev/null || exit
  git rev-list --left-right --count '@{u}...HEAD' 2>/dev/null | awk '{printf "%s behind, %s ahead", $1, $2}'
)
SPINE_PULL_FAILED=0; SPINE_PULL_STATE=""
if ! (cd "$SPINE" && git pull --ff-only --quiet 2>/dev/null); then
  SPINE_PULL_FAILED=1; SPINE_PULL_STATE="$(pull_state "$SPINE")"
fi

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
cwd_real="$(pwd -P 2>/dev/null)"
IS_CODE_LANE=0; CODE_NAME=""; CODE_PULL_FAILED=0; CODE_PULL_STATE=""; MIRROR_CWD=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  top=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ "$top" != "$SPINE" ] && [ -n "$top" ]; then
    if ! git pull --ff-only --quiet 2>/dev/null; then
      CODE_PULL_FAILED=1; CODE_PULL_STATE="$(pull_state "$top")"
    fi
    IS_CODE_LANE=1
    CODE_NAME=$(basename "$top")
  fi
fi

# A code lane addressed by its mirror: cwd is spine/projects/<name>/. git toplevel is
# the spine, so the check above calls it workspace-root, but opening a terminal there
# means "I am working that lane", not "I own the spine". Classify it as the lane,
# matching scripts/hooks/block-cross-lane-write.py.
if [ "$IS_CODE_LANE" = "0" ]; then
  case "$cwd_real/" in
    "$SPINE/projects/"*)
      rest="${cwd_real#"$SPINE"/projects/}"
      cand="${rest%%/*}"
      if [ -n "$cand" ] && [ -d "$SPINE/projects/$cand" ]; then
        IS_CODE_LANE=1; CODE_NAME="$cand"; MIRROR_CWD=1
      fi
      ;;
  esac
fi

IS_DESK=0; DESK_NAME=""
if [ "$IS_CODE_LANE" = "0" ]; then
  case "$cwd_real/" in
    "$SPINE/desks/"*)
      rest="${cwd_real#"$SPINE"/desks/}"
      DESK_NAME="${rest%%/*}"
      [ -n "$DESK_NAME" ] && IS_DESK=1
      ;;
  esac
fi

# --- shared trailer: drafts, pull state, switchboard --------------------------
trailer() {
  draft_count=$(find "$SPINE/brain/drafts" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  if [ "${draft_count:-0}" -gt 0 ]; then
    echo "ACTION: brain/drafts/ holds ${draft_count} staged file(s) awaiting a spine-session merge (/catchup drains them)."
  fi
  [ "$SPINE_PULL_FAILED" = "1" ] && echo "NOTE: spine pull FAILED (${SPINE_PULL_STATE:-diverged or offline}); files may be stale."
  [ "$CODE_PULL_FAILED" = "1" ] && echo "NOTE: code repo pull FAILED (${CODE_PULL_STATE:-diverged or offline}); files may be stale."
  SB_STATE="$SPINE/switchboard/state.json"
  if [ -f "$SB_STATE" ]; then
    sb_built=$(grep -o '"built_human"[^,]*' "$SB_STATE" 2>/dev/null | head -1 | cut -d'"' -f4)
    sb_n=$(grep -c '"head"' "$SB_STATE" 2>/dev/null | tr -d ' ')
    echo "SWITCHBOARD: ${sb_n:-0} lanes mapped (built ${sb_built:-never}). What moved in the OTHER windows: ${SPINE}/switchboard/SWITCHBOARD.html. A lane's 'focus' line in switchboard/state.json says what it is on; overlap means ask that session, never write into its lane."
  fi
  echo "=== END SESSION CONTEXT ==="
}

READ_PREAMBLE='=== READ NOW (blocking): Read every file below before your first reply. ===
Only these PATHS reached you, not the contents. The index files are tables of contents, not substitutes. Treat these as ground truth over assumptions.'

# --- emit the compact, lane-aware read-directive -----------------------------
if [ "$IS_CODE_LANE" = "1" ] && [ -n "$CODE_NAME" ]; then
  PDIR="$SPINE/projects/$CODE_NAME"
  if [ "$MIRROR_CWD" = "1" ]; then
    WHERE="cwd is ${SPINE}/projects/${CODE_NAME}/, the spine-side MIRROR: you are in the ${CODE_NAME} LANE, not a spine session. Being inside the spine does not make this a spine session"
  else
    WHERE="cwd is the ${CODE_NAME} repo, NOT the spine"
  fi
  cat <<RULE
=== CODE LANE: ${CODE_NAME} (${WHERE}) ===

WRITE LANE: write only under the ${CODE_NAME} repo, ${SPINE}/projects/${CODE_NAME}/, and ${SPINE}/brain/drafts/.
FORBIDDEN even if asked: writing ${SPINE}/brain/ (except drafts/), /memory/, /global/, /skills/, or any other projects/<name>/. Decline before the write and redirect: open a spine session, or stage in brain/drafts/. A PreToolUse guard (scripts/hooks/block-cross-lane-write.py) blocks it anyway.
A lane you cannot write is still a lane you can drive: cd <that repo> && claude -p "<goal>".

${READ_PREAMBLE}
  - ${SPINE}/brain/ACTIVE_NOW.md   (cross-cutting priorities)
  - ${SPINE}/brain/CONCERNS.md     (open loops, each with its Probe or Owner)
RULE
  [ -f "$PDIR/STATUS.md" ] && echo "  - $PDIR/STATUS.md   (THIS lane's live state)"
  [ -f "$PDIR/MEMORY.md" ] && echo "  - $PDIR/MEMORY.md   (THIS lane's durable facts; outranks STATUS.md when they disagree)"
  echo "On demand, in ${SPINE}/brain/ : WHO_I_AM.md, PEOPLE.md, DECISIONS.md, WEEKLY_LOG.md"
  trailer
elif [ "$IS_DESK" = "1" ] && [ -n "$DESK_NAME" ]; then
  DDIR="$SPINE/desks/$DESK_NAME"
  cat <<RULE
=== DESK: ${DESK_NAME} (cwd is desks/${DESK_NAME}, a TOPIC lane) ===

WRITE LANE: write only under ${DDIR}/ and ${SPINE}/brain/drafts/.
FORBIDDEN even if asked: writing ${SPINE}/brain/ (except drafts/), /memory/, /global/, /skills/, any other desk, or any code repo. Stage cross-cutting facts in brain/drafts/, or open the right lane. A PreToolUse guard (scripts/hooks/block-cross-lane-write.py) blocks it anyway.

${READ_PREAMBLE}
Read your desk's OWN CLAUDE.md FIRST: it names your context slice + posture. Do NOT load the whole brain; a desk reads its slice.
  - ${DDIR}/CLAUDE.md   (this desk's contract)
RULE
  [ -f "$DDIR/LOG.md" ] && echo "  - $DDIR/LOG.md   (this desk's running record)"
  trailer
else
  cat <<RULE
=== SPINE SESSION (workspace-root) ===

${READ_PREAMBLE}
  - ${SPINE}/brain/ACTIVE_NOW.md   (cross-cutting priorities)
  - ${SPINE}/brain/CONCERNS.md     (open loops, each with its Probe or Owner)
On demand: ${SPINE}/brain/ WHO_I_AM.md, PEOPLE.md, DECISIONS.md, WEEKLY_LOG.md
Durable per-lane facts live in ${SPINE}/projects/<name>/MEMORY.md. Read it before asserting one; STATUS.md is session state and goes stale.
RULE
  trailer
fi

# --- cross-lane awareness: refresh the local switchboard cache (best-effort) --
( python3 "$SPINE/scripts/build-switchboard.py" >/dev/null 2>&1 & ) 2>/dev/null

exit 0
