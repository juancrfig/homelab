# Topic: text-processing/grep

## Why this topic matters
`grep` is the fastest way to answer "is this thing here, and where" across logs,
configs, and source trees. Knowing its flags cold — recursion, line numbers, context,
inversion, fixed-string vs regex — saves minutes on every single incident and is one
of the most interview-tested "do you actually use Linux daily" checks.

## Scope / sub-skills to test
- Recursive search across a directory tree (`-r`/`-R`), with file:line output (`-n`).
- Case-insensitive search (`-i`).
- Inverting a match — lines that do NOT contain a pattern (`-v`).
- Counting matches (`-c`) vs listing matching filenames only (`-l`).
- Context lines around a match (`-A`/`-B`/`-C`).
- Fixed-string search to avoid regex metacharacter surprises (`-F`/`fgrep`).
- Basic vs extended regex distinctions relevant to grep (`-E` for `|`, `+`, `{}` without
  escaping).
- Conceptual: how grep fits with `find`/`xargs` for "search then act" workflows.

## Out of scope
- Full regex theory (lookaheads, backreferences) beyond what POSIX ERE supports.
- `ripgrep`/`ag`/other modern alternatives — grep itself is the target tool here.
- `awk`/`sed` text transformation (different topic; grep is search-only).

## Common real-world scenarios
- "Find every config file under /etc that still references an old hostname."
- "How many error lines are in this log, and which files have them, without drowning
  in the matches themselves."
- "Show me 3 lines of context around each timeout error so I can see what led to it."
- Combining grep with permissions: locating files that mention a secret pattern, then
  checking who can read them via ACL.

## Gotchas
- Forgetting `-r` and grep only checking files literally named on the command line.
- Regex metacharacters (`.`, `*`, `[`) in what looks like a literal string silently
  changing the match — when in doubt, `-F`.
- `-i` is case-insensitive on the whole match, not just the first character — easy to
  assume otherwise.
