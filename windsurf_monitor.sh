#!/usr/bin/env bash         # ← shebang を bash に
WATCH="$HOME/.codeium/windsurf/cascade"

fswatch -0 -t --event=Updated "$WATCH" | \
while IFS= read -r -d '' time path; do
  printf '%(%F %T)T BUSY  %s\n' "${time%.*}" "$path"
done
