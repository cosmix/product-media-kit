# Session Conduct

> Lead-agent conduct: edits handed back to the user instead of made

## Handing doable edits back to the user

**What happened**: a review left .claude/skills/install/SKILL.md stale because a subagent's Bash sandbox blocked writes to .claude/skills; the lead reported it as an open item and asked twice instead of editing it.
**Why**: the Bash sandbox write list was read as a limit on all edits, and the user's request to add the feature already covered the skill.
**Prevention**: the Edit and Write tools are not bound by the Bash sandbox; when a change the user asked for needs a file the sandbox blocks for Bash, edit it with Edit/Write (the permission prompt is the user's check) and only report it if that is denied.
**Fix**: the lead edited the skill with the Edit tool.
