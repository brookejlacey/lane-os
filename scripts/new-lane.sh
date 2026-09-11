#!/usr/bin/env bash
# Scaffold a new lane. Usage:
#   scripts/new-lane.sh code   <name>   # mirror folder for a code repo
#   scripts/new-lane.sh desk   <name>   # a new topic desk
#   scripts/new-lane.sh voice  <name>   # a new voice register (a desk with a corpus)
set -euo pipefail
SPINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
kind="${1:-}"; name="${2:-}"
[ -z "$kind" ] || [ -z "$name" ] && { echo "usage: new-lane.sh code|desk|voice <name>"; exit 1; }

case "$kind" in
  code)
    dest="$SPINE/projects/$name"
    [ -d "$dest" ] && { echo "exists: $dest"; exit 1; }
    cp -R "$SPINE/projects/_TEMPLATE" "$dest"
    sed -i.bak "s/_TEMPLATE/$name/g" "$dest"/*.md && rm -f "$dest"/*.bak
    echo "created $dest (mirror for the code repo named '$name')"
    echo "Open a session in the actual code repo to start building."
    ;;
  desk)
    dest="$SPINE/desks/$name"
    [ -d "$dest" ] && { echo "exists: $dest"; exit 1; }
    cp -R "$SPINE/desks/_TEMPLATE" "$dest"
    sed -i.bak "s/_TEMPLATE/$name/g" "$dest"/*.md && rm -f "$dest"/*.bak
    echo "created desk $dest"
    echo "Fill $dest/CLAUDE.md, then open a session there."
    ;;
  voice)
    dest="$SPINE/desks/$name"
    [ -d "$dest" ] && { echo "exists: $dest"; exit 1; }
    cp -R "$SPINE/desks/_TEMPLATE-voice" "$dest"
    # Every file, not just the top level: the corpus README and voice.toml carry the
    # register name too, and a half-renamed register points the linter at the template.
    find "$dest" -type f \( -name '*.md' -o -name '*.toml' \) -exec sed -i.bak "s/_TEMPLATE/$name/g" {} +
    find "$dest" -name '*.bak' -delete
    echo "created voice register $dest"
    echo "Fill $dest/CLAUDE.md and $dest/VOICE.md, pull raw samples into $dest/corpus/,"
    echo "then: python3 scripts/check-voice.py --measure desks/$name --write"
    ;;
  *) echo "unknown kind: $kind (use code|desk|voice)"; exit 1 ;;
esac
