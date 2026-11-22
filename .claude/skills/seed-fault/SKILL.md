---
name: seed-fault
description: Deliberately break the pipeline with one described fault, record the red test and hook output, then restore. Use when asked to seed, inject, or test a fault against the verification suite.
allowed-tools: Read, Edit, Bash(python -m pytest*), Bash(make*), Bash(git*)
---
# Seeding a fault: $ARGUMENTS

Start clean: `git status --short` must print nothing. If not, stop.

1. State in one sentence which test or hook SHOULD catch `$ARGUMENTS`.
2. Make the smallest edit that introduces it. Show `git diff`.
3. Run `make test 2>&1 | tail -30`, then pipe a PostToolUse payload to the hook:
   `printf '{"tool_input":{"file_path":"%s/src/features.py"}}' "$PWD" | CLAUDE_PROJECT_DIR=$PWD .claude/hooks/check_leakage.sh; echo exit=$?`
   Paste both outputs verbatim into docs/SEEDED_FAULTS.md. Never paraphrase them.
4. If everything stays green, that is the finding: the suite has a gap. Write the
   missing test FIRST, commit it, and re-seed.
5. Commit the fault ("SEEDED FAULT: ..."), restore with `git checkout HEAD~1 -- <file>`,
   commit the fix, and confirm `make test` is green.
6. Record how many turns the fix took, and anything the hook could not see.
