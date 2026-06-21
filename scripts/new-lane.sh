#!/usr/bin/env bash
# Scaffold a new lane. Usage:
#   scripts/new-lane.sh code   <name>   # mirror folder for a code repo
#   scripts/new-lane.sh desk   <name>   # a new topic desk
set -euo pipefail
SPINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
kind="${1:-}"; name="${2:-}"
[ -z "$kind" ] || [ -z "$name" ] && { echo "usage: new-lane.sh code|desk <name>"; exit 1; }

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
  *) echo "unknown kind: $kind (use code|desk)"; exit 1 ;;
esac
