#!/usr/bin/env bash
# lane-doctor: a cheap, mechanical health check for a Lane OS spine.
#
# Catches the drift a fork accumulates over time, with nothing but grep/find:
#   1. Dangling [[wikilinks]] - a link whose target memory file does not exist.
#   2. Unindexed memory - a memory/*.md that the MEMORY.md index never lists.
#
# This is the Lane OS answer to gbrain's `doctor` / `orphans`: same idea, no database.
# It scans only the dirs where wikilinks are real DATA (brain, memory, projects, desks)
# and skips READMEs, examples, and _TEMPLATE folders, which teach the [[link]] syntax
# in prose and would otherwise look like dangling links.
#
# Run from the spine root. Exits 1 if any FAIL is found, else 0. WARN does not fail.
set -euo pipefail
cd "$(dirname "$0")/.."

fail=0
say() { printf '%s\n' "$*"; }
SCAN=(brain memory projects desks)
EXCL=(--include='*.md' --exclude='README.md' --exclude-dir='examples' --exclude-dir='_TEMPLATE')

# ---------- 1. Dangling wikilinks ----------
say "== wikilinks =="
links=$(grep -rho '\[\[[^][]*\]\]' "${EXCL[@]}" "${SCAN[@]}" 2>/dev/null \
          | sed 's/^\[\[//; s/\]\]$//' | sort -u || true)
dangling=0
if [ -n "${links}" ]; then
  while IFS= read -r slug; do
    [ -z "$slug" ] && continue
    if ! find . -path ./.git -prune -o -name "${slug}.md" -print 2>/dev/null | grep -q .; then
      say "  FAIL dangling [[${slug}]] (no ${slug}.md exists)"
      dangling=$((dangling+1)); fail=1
    fi
  done <<< "$links"
fi
[ "$dangling" = 0 ] && say "  ok: every [[wikilink]] in the spine resolves"

# ---------- 2. Memory index sync ----------
say "== memory index =="
INDEX="memory/MEMORY.md"
if [ ! -f "$INDEX" ]; then
  say "  WARN no memory/MEMORY.md index found"
else
  unindexed=0
  while IFS= read -r f; do
    base=$(basename "$f")
    case "$base" in MEMORY.md|README.md) continue;; esac
    slug="${base%.md}"
    if ! grep -q "$base" "$INDEX" && ! grep -q "\[\[${slug}\]\]" "$INDEX"; then
      say "  WARN ${f} is not referenced in MEMORY.md (unindexed)"
      unindexed=$((unindexed+1))
    fi
  done < <(find memory -maxdepth 1 -name '*.md' 2>/dev/null | sort)
  [ "$unindexed" = 0 ] && say "  ok: every memory fact is in the index"
fi

say ""
if [ "$fail" = 0 ]; then say "lane-doctor: PASS"; else say "lane-doctor: FAIL (fix the dangling links above)"; fi
exit "$fail"
