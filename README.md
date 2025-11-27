# Gmail API Skill

A Claude Agent Skill for Gmail operations via CLI. Read, draft, send, archive, label, and batch-process emails.

## Setup

1. **Create OAuth credentials** at [Google Cloud Console](https://console.cloud.google.com/apis/credentials):
   - Create project → Enable Gmail API
   - Configure OAuth consent screen (External, add yourself as test user)
   - Create OAuth Client ID (Desktop app)

2. **Configure credentials**:
   ```bash
   cp credentials.example.json credentials.json
   # Edit credentials.json with your client_id and client_secret
   ```

3. **Install dependencies**:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

4. **First run** opens browser for OAuth consent:
   ```bash
   .venv/bin/python scripts/gmail.py read --limit 3
   ```

## Usage

```bash
# Read emails
scripts/gmail.py read --limit 10
scripts/gmail.py read --query "is:unread" --full

# Create draft
scripts/gmail.py draft --to "x@y.com" --subject "Hi" --body "Hello"
scripts/gmail.py draft --reply-to MSG_ID --body "Thanks!"

# Send
scripts/gmail.py send --draft-id DRAFT_ID
scripts/gmail.py send --to "x@y.com" --subject "Hi" --body "Hello"

# Manage
scripts/gmail.py archive --id MSG_ID
scripts/gmail.py trash --id MSG_ID
scripts/gmail.py mark-read --id MSG_ID

# Batch operations
scripts/gmail.py batch-archive --query "from:newsletters@"
```

Run `scripts/gmail.py --help` for all 24 commands.

## As a Claude Skill

This repo follows the [Agent Skills spec](https://docs.claude.com/en/docs/claude-code/skills). Drop it in your skills directory and Claude will discover it via the `SKILL.md` metadata.

## License

MIT
