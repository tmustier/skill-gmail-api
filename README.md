# Gmail API Skill

CLI tool for reading emails, creating drafts, and sending messages via Gmail API.

## Setup

1. **Create OAuth credentials** at [Google Cloud Console](https://console.cloud.google.com/apis/credentials):
   - Create project → Enable Gmail API
   - Configure OAuth consent screen (External, add yourself as test user)
   - Create OAuth Client ID (Desktop app)
   - Copy client ID and secret into `credentials.json`

2. **Install dependencies** (already done if using provided venv):
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. **First run** - opens browser for OAuth consent:
   ```bash
   .venv/bin/python gmail.py read --limit 3
   ```

## Usage

```bash
# Read emails
.venv/bin/python gmail.py read --limit 10
.venv/bin/python gmail.py read --query "is:unread"
.venv/bin/python gmail.py read --query "from:someone@example.com" --full

# Get specific message
.venv/bin/python gmail.py get --id MESSAGE_ID

# Create draft
.venv/bin/python gmail.py draft --to "x@y.com" --subject "Hi" --body "Hello"
.venv/bin/python gmail.py draft --reply-to MESSAGE_ID --body "Thanks!"

# List/delete drafts
.venv/bin/python gmail.py list-drafts
.venv/bin/python gmail.py delete-draft --draft-id DRAFT_ID

# Send
.venv/bin/python gmail.py send --draft-id DRAFT_ID
.venv/bin/python gmail.py send --to "x@y.com" --subject "Hi" --body "Hello"
```

## Files

| File | Description |
|------|-------------|
| `gmail.py` | Main CLI |
| `auth.py` | OAuth token management |
| `credentials.json` | Your OAuth client ID/secret (not committed) |
| `token.json` | Cached auth token (auto-generated, not committed) |
