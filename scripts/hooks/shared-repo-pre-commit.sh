#!/usr/bin/env bash
# Second lock on a repo that is read by someone outside your workspace.
#
# scripts/publish-shared-repo.py in the spine is the only thing that should ever commit
# here, and it allowlists what it stages. This hook covers the other path: a person or an
# agent running `git commit` inside this checkout by hand. It refuses any staged file
# that is not in the publisher's own manifest. inbox/ is the reader's, and is exempt.
#
# Why two locks: the rules sync once DISCOVERED a shared checkout (it carried a generated
# copy) and wrote the full constitution into it. The sync's deny list now derives from
# the publisher's audiences, and this hook is the independent second guard. One lock is
# not a lock.
set -uo pipefail
repo="$(git rev-parse --show-toplevel)"
manifest="$repo/.published-manifest"

allowed=$'.gitignore\n.published-manifest'
if [ -f "$manifest" ]; then allowed="$allowed"$'\n'"$(cat "$manifest")"; fi

bad=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  case "$f" in inbox/*) continue ;; esac
  printf '%s\n' "$allowed" | grep -qxF -- "$f" || bad="$bad  $f"$'\n'
done < <(git diff --cached --name-only --diff-filter=ACMR)

if [ -n "$bad" ]; then
  echo "COMMIT BLOCKED. This repo is read outside the workspace." >&2
  echo "These staged files are not in the publisher's manifest:" >&2
  printf '%s' "$bad" >&2
  echo "Edit the source lane in the spine and run scripts/publish-shared-repo.py." >&2
  exit 1
fi
exit 0
