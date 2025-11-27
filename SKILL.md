---
name: skill-gmail-api
description: |
  Gmail API skill for email operations via CLI. Supports reading, drafting, sending, archiving, labeling, and batch operations.
  Use when user needs to: read emails, create/send drafts, reply to messages, archive/trash messages, manage labels, or perform bulk email operations.
allowed-tools:
  - Execute
---

# Gmail API Skill

CLI at `~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py`

## Quick Reference

```bash
# Read
gmail.py read --limit 10
gmail.py read --query "is:unread" --full
gmail.py get --id MSG_ID

# Draft & Send  
gmail.py draft --to "x@y.com" --subject "Hi" --body "Hello"
gmail.py draft --reply-to MSG_ID --body "Thanks!"
gmail.py send --draft-id DRAFT_ID
gmail.py send --to "x@y.com" --subject "Hi" --body "Hello"

# Manage
gmail.py archive --id MSG_ID
gmail.py trash --id MSG_ID
gmail.py star --id MSG_ID
gmail.py mark-read --id MSG_ID

# Batch
gmail.py batch-archive --query "from:newsletters@"
gmail.py batch-mark-read --query "is:unread from:notifications@"
```

Run `gmail.py --help` or `gmail.py COMMAND --help` for options.

**Full command reference**: See [references/commands.md](references/commands.md)

## Setup

1. Create OAuth credentials at [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Add client_id and client_secret to `credentials.json`
3. First run opens browser for OAuth consent
