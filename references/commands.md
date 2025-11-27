# Gmail CLI Command Reference

Run from skill directory: `scripts/gmail.py COMMAND [OPTIONS]`

## Reading

```bash
read --limit N [--query Q] [--full]     # List emails (--full for body + attachments)
get --id MSG_ID                          # Get single message with body + attachments
get-thread --id THREAD_ID [--full]       # Get all messages in thread
```

### Search Query Examples
- `is:unread` - Unread messages
- `from:someone@example.com` - From specific sender
- `subject:meeting` - Subject contains "meeting"
- `after:2024/01/01` - After date
- `has:attachment` - Has attachments
- `in:sent` - Sent messages
- `label:important` - With label

## Drafts

```bash
draft --to X --subject Y --body Z        # New draft
draft --reply-to MSG_ID --body Z         # Reply draft (auto-fills to/subject)
draft --to X --subject Y --body Z --attach /path/to/file.pdf
draft --to X --subject Y --body Z --attach file1.pdf --attach file2.docx
list-drafts                              # List all drafts
delete-draft --draft-id ID               # Delete draft
```

## Sending

```bash
send --draft-id ID                       # Send existing draft
send --to X --subject Y --body Z         # Send directly
send --to X --subject Y --body Z --attach /path/to/file.pdf
send --to X --subject Y --body Z --html  # Send HTML email
```

## Attachments

```bash
# Attachments are shown in message output when using --full or get command
# Output includes: filename, mimeType, size, attachmentId

download-attachment --message-id MSG_ID --attachment-id ATT_ID
download-attachment --message-id MSG_ID --attachment-id ATT_ID -o /path/to/save.pdf
```

## Message Management

```bash
archive --id MSG_ID                      # Remove from inbox
trash --id MSG_ID                        # Move to trash
untrash --id MSG_ID                      # Restore from trash
delete --id MSG_ID                       # Permanent delete (!)
mark-read --id MSG_ID
mark-unread --id MSG_ID
star --id MSG_ID
unstar --id MSG_ID
```

## Labels

```bash
list-labels                              # List all labels
create-label --name "My Label"           # Create label
delete-label --id LABEL_ID               # Delete label
modify-labels --id MSG_ID --add LABEL_ID --remove LABEL_ID
```

## Threads

```bash
get-thread --id THREAD_ID [--full]       # Get conversation
archive-thread --id THREAD_ID            # Archive whole thread
trash-thread --id THREAD_ID              # Trash whole thread
```

## Filters

```bash
list-filters                             # List all filters
get-filter --id FILTER_ID                # Get filter details
delete-filter --id FILTER_ID             # Delete filter

# Create filter with criteria and actions
create-filter --from "newsletter@x.com" --archive
create-filter --from "boss@company.com" --star --add-label IMPORTANT
create-filter --subject "[URGENT]" --add-label Label_123 --mark-read
create-filter --has-attachment --add-label Label_Attachments
create-filter --query "unsubscribe" --archive --mark-read
```

### Filter Criteria Options
- `--from ADDRESS` - Match sender
- `--to ADDRESS` - Match recipient
- `--subject TEXT` - Match subject
- `--query QUERY` - Gmail search query
- `--has-attachment` - Has attachments

### Filter Action Options
- `--add-label LABEL_ID` - Add label (can repeat)
- `--remove-label LABEL_ID` - Remove label (can repeat)
- `--archive` - Remove from INBOX
- `--mark-read` - Mark as read
- `--star` - Star message
- `--forward ADDRESS` - Forward to address

## Batch Operations

```bash
batch-archive --query "from:newsletters@" --limit 100
batch-trash --query "older_than:30d" --limit 50
batch-mark-read --query "from:notifications@" --limit 100
```

## Output Format

All commands output JSON:
```json
{"status": "sent", "message_id": "...", "thread_id": "..."}
```

Messages with `--full` include attachments:
```json
{
  "id": "...",
  "subject": "...",
  "body": "...",
  "attachments": [
    {"filename": "doc.pdf", "mimeType": "application/pdf", "size": 12345, "attachmentId": "..."}
  ]
}
```
