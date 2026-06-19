# Topic: permissions/acl

## Why this topic matters
The owner/group/other model can't express "this one extra user/group needs access"
without changing ownership. POSIX ACLs (`setfacl`/`getfacl`) are how real systems grant
narrow, additional access — shared config files, deploy users, audit accounts — without
loosening the traditional bits for everyone. Misreading `getfacl` output or forgetting
the mask is a recurring real-incident source (silently-too-broad or silently-too-narrow
access).

## Scope / sub-skills to test
- Reading `getfacl` output: named user/group entries vs the base owner/group/other,
  and the `mask` entry.
- Granting a specific user or group read-only / rwx access via `setfacl -m`.
- Removing a single ACL entry (`setfacl -x`) vs stripping all extended ACLs (`setfacl -b`).
- Default ACLs on a directory (`setfacl -d`) so new files inherit access automatically.
- The ACL mask: what it caps, and recomputing it after adding entries (`setfacl -m m::`
  or `setfacl -b` then re-add, or `-n` to skip recompute).
- Conceptual: why ACLs exist (beyond owner/group/other), and what they do NOT change
  (ownership, the traditional permission bits themselves).

## Out of scope
- NFSv4 ACLs / Windows ACLs (different model entirely).
- SELinux/AppArmor contexts (a separate, orthogonal access-control layer).
- Filesystem support nuances (which filesystems support ACLs) beyond a passing mention.

## Common real-world scenarios
- A CI user needs read access to a secrets file owned by another user, without joining
  its group or changing ownership.
- A shared `/srv/app` directory where every new deploy artifact must be readable by an
  `audit` group automatically, without a post-deploy chmod step.
- Diagnosing "why can this user read the file" when `ls -l` alone doesn't explain it
  (the `+` suffix on permissions hints at an ACL).

## Gotchas
- `chmod` on the group bits can rewrite the ACL mask and silently narrow access granted
  via ACL entries — order of operations matters.
- The `+` after permission bits in `ls -l` means "this file has an extended ACL" — easy
  to miss.
- `setfacl -m` is additive; people often reach for `-x`/`-b` incorrectly when they meant
  to just adjust one entry.
