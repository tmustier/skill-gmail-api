---
name: skill-gmail-api
description: |
  Gmail API skill for reading emails, creating drafts, and sending messages.
  Use this skill when you need to:
  - Read recent emails from the user's inbox
  - Create draft emails (including reply drafts)
  - Send emails directly or from drafts
  
  CLI Usage:
    ~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py --help
    ~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py read --limit 10
    ~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py draft --to "x@y.com" --subject "Hi" --body "Hello"
    ~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py send --draft-id "r123"
allowed-tools:
  - Execute
---

# Gmail API Skill

## Setup (One-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app type)
5. Download credentials and save as `~/skill-gmail-api/credentials.json`
6. Run any command - it will open browser for OAuth consent

## Commands

### Read emails
```bash
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py read --limit 10
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py read --query "from:bob@example.com"
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py read --query "is:unread" --limit 5
```

### Create draft
```bash
# New email
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py draft --to "x@y.com" --subject "Hello" --body "Hi there"

# Reply to existing message
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py draft --reply-to MSG_ID --body "Thanks for your email"

# With CC/BCC
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py draft --to "x@y.com" --cc "y@y.com" --subject "Hi" --body "Hello"
```

### Send email
```bash
# Send existing draft
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py send --draft-id DRAFT_ID

# Send directly (no draft)
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py send --to "x@y.com" --subject "Hello" --body "Hi there"
```

### Get message details
```bash
~/skill-gmail-api/.venv/bin/python ~/skill-gmail-api/gmail.py get --id MSG_ID
```
