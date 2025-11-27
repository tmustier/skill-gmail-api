#!/usr/bin/env python3
"""Gmail CLI - read emails, create drafts, send messages."""

import base64
import json
import mimetypes
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

import click

from auth import get_gmail_service


def attach_file(msg: MIMEMultipart, file_path: str) -> None:
    """Attach a file to the message."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Attachment not found: {file_path}")
    
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    main_type, sub_type = mime_type.split("/", 1)
    
    with open(path, "rb") as f:
        part = MIMEBase(main_type, sub_type)
        part.set_payload(f.read())
    
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=path.name)
    msg.attach(part)


def get_attachments_info(payload: dict) -> list:
    """Extract attachment info from message payload."""
    attachments = []
    
    def process_parts(parts):
        for part in parts:
            filename = part.get("filename")
            if filename:
                body = part.get("body", {})
                attachments.append({
                    "filename": filename,
                    "mimeType": part.get("mimeType", ""),
                    "size": body.get("size", 0),
                    "attachmentId": body.get("attachmentId", ""),
                })
            if "parts" in part:
                process_parts(part["parts"])
    
    if "parts" in payload:
        process_parts(payload["parts"])
    
    return attachments


def encode_message(message: MIMEText | MIMEMultipart) -> str:
    """Encode MIME message to base64url string."""
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def decode_body(payload: dict) -> str:
    """Extract plain text body from message payload."""
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                if part["body"].get("data"):
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            elif "parts" in part:
                result = decode_body(part)
                if result:
                    return result
    return ""


def get_header(headers: list, name: str) -> str:
    """Get header value by name."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def format_message_summary(msg: dict) -> dict:
    """Format message into summary dict."""
    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "from": get_header(headers, "From"),
        "to": get_header(headers, "To"),
        "subject": get_header(headers, "Subject"),
        "date": get_header(headers, "Date"),
        "snippet": msg.get("snippet", ""),
    }


def format_message_full(msg: dict) -> dict:
    """Format message with full body."""
    summary = format_message_summary(msg)
    payload = msg.get("payload", {})
    summary["body"] = decode_body(payload)
    summary["labelIds"] = msg.get("labelIds", [])
    summary["attachments"] = get_attachments_info(payload)
    return summary


@click.group()
def cli():
    """Gmail CLI - read, draft, and send emails."""
    pass


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of messages to retrieve")
@click.option("--query", "-q", default="", help="Gmail search query (e.g., 'is:unread', 'from:x@y.com')")
@click.option("--full", is_flag=True, help="Include full message body")
def read(limit: int, query: str, full: bool):
    """Read emails from inbox."""
    service = get_gmail_service()
    
    results = service.users().messages().list(
        userId="me",
        maxResults=limit,
        q=query or None,
    ).execute()
    
    messages = results.get("messages", [])
    if not messages:
        click.echo(json.dumps({"messages": [], "count": 0}))
        return
    
    output = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="full" if full else "metadata",
            metadataHeaders=["From", "To", "Subject", "Date"] if not full else None,
        ).execute()
        
        if full:
            output.append(format_message_full(msg))
        else:
            output.append(format_message_summary(msg))
    
    click.echo(json.dumps({"messages": output, "count": len(output)}, indent=2))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID to retrieve")
def get(msg_id: str):
    """Get full details of a specific message."""
    service = get_gmail_service()
    
    msg = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="full",
    ).execute()
    
    click.echo(json.dumps(format_message_full(msg), indent=2))


@cli.command()
@click.option("--to", "to_addr", help="Recipient email address")
@click.option("--cc", help="CC recipients (comma-separated)")
@click.option("--bcc", help="BCC recipients (comma-separated)")
@click.option("--subject", help="Email subject")
@click.option("--body", required=True, help="Email body text")
@click.option("--html", is_flag=True, help="Treat body as HTML")
@click.option("--reply-to", "reply_to", help="Message ID to reply to")
@click.option("--attach", "attachments", multiple=True, help="File path to attach (can use multiple times)")
def draft(to_addr: Optional[str], cc: Optional[str], bcc: Optional[str], 
          subject: Optional[str], body: str, html: bool, reply_to: Optional[str],
          attachments: tuple):
    """Create a draft email."""
    service = get_gmail_service()
    
    thread_id = None
    orig_headers = []
    
    if reply_to:
        original = service.users().messages().get(
            userId="me",
            id=reply_to,
            format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID"],
        ).execute()
        
        orig_headers = original.get("payload", {}).get("headers", [])
        thread_id = original.get("threadId")
        
        if not to_addr:
            to_addr = get_header(orig_headers, "From")
        if not subject:
            orig_subject = get_header(orig_headers, "Subject")
            subject = f"Re: {orig_subject}" if not orig_subject.lower().startswith("re:") else orig_subject
    
    if not to_addr:
        click.echo("Error: --to is required (unless using --reply-to)", err=True)
        sys.exit(1)
    if not subject:
        click.echo("Error: --subject is required (unless using --reply-to)", err=True)
        sys.exit(1)
    
    # Use multipart if attachments or HTML
    if attachments or html:
        msg = MIMEMultipart()
        if html:
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))
        for file_path in attachments:
            attach_file(msg, file_path)
    else:
        msg = MIMEText(body)
    
    msg["To"] = to_addr
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    
    if reply_to:
        orig_msg_id = get_header(orig_headers, "Message-ID")
        if orig_msg_id:
            msg["In-Reply-To"] = orig_msg_id
            msg["References"] = orig_msg_id
    
    draft_body = {"message": {"raw": encode_message(msg)}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id
    
    result = service.users().drafts().create(userId="me", body=draft_body).execute()
    
    click.echo(json.dumps({
        "status": "created",
        "draft_id": result["id"],
        "message_id": result["message"]["id"],
        "thread_id": result["message"].get("threadId"),
    }, indent=2))


@cli.command()
@click.option("--draft-id", help="Draft ID to send")
@click.option("--to", "to_addr", help="Recipient (for direct send without draft)")
@click.option("--cc", help="CC recipients (comma-separated)")
@click.option("--subject", help="Email subject (for direct send)")
@click.option("--body", help="Email body (for direct send)")
@click.option("--html", is_flag=True, help="Treat body as HTML")
@click.option("--attach", "attachments", multiple=True, help="File path to attach (can use multiple times)")
def send(draft_id: Optional[str], to_addr: Optional[str], cc: Optional[str],
         subject: Optional[str], body: Optional[str], html: bool, attachments: tuple):
    """Send an email (from draft or directly)."""
    service = get_gmail_service()
    
    if draft_id:
        result = service.users().drafts().send(
            userId="me",
            body={"id": draft_id}
        ).execute()
        
        click.echo(json.dumps({
            "status": "sent",
            "message_id": result["id"],
            "thread_id": result.get("threadId"),
            "label_ids": result.get("labelIds", []),
        }, indent=2))
    
    elif to_addr and subject and body:
        if attachments or html:
            msg = MIMEMultipart()
            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))
            for file_path in attachments:
                attach_file(msg, file_path)
        else:
            msg = MIMEText(body)
        
        msg["To"] = to_addr
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        
        result = service.users().messages().send(
            userId="me",
            body={"raw": encode_message(msg)}
        ).execute()
        
        click.echo(json.dumps({
            "status": "sent",
            "message_id": result["id"],
            "thread_id": result.get("threadId"),
            "label_ids": result.get("labelIds", []),
        }, indent=2))
    
    else:
        click.echo("Error: provide --draft-id OR (--to, --subject, --body)", err=True)
        sys.exit(1)


@cli.command()
def list_drafts():
    """List all drafts."""
    service = get_gmail_service()
    
    results = service.users().drafts().list(userId="me").execute()
    drafts = results.get("drafts", [])
    
    output = []
    for draft_ref in drafts:
        draft = service.users().drafts().get(
            userId="me",
            id=draft_ref["id"],
            format="metadata",
        ).execute()
        
        msg = draft.get("message", {})
        headers = msg.get("payload", {}).get("headers", [])
        
        output.append({
            "draft_id": draft["id"],
            "message_id": msg.get("id"),
            "to": get_header(headers, "To"),
            "subject": get_header(headers, "Subject"),
            "snippet": msg.get("snippet", ""),
        })
    
    click.echo(json.dumps({"drafts": output, "count": len(output)}, indent=2))


@cli.command()
@click.option("--draft-id", required=True, help="Draft ID to delete")
def delete_draft(draft_id: str):
    """Delete a draft."""
    service = get_gmail_service()
    service.users().drafts().delete(userId="me", id=draft_id).execute()
    click.echo(json.dumps({"status": "deleted", "draft_id": draft_id}))


# === Message Management ===

@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def archive(msg_id: str):
    """Archive a message (remove from INBOX)."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me", id=msg_id,
        body={"removeLabelIds": ["INBOX"]}
    ).execute()
    click.echo(json.dumps({"status": "archived", "id": msg_id}))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def trash(msg_id: str):
    """Move a message to trash."""
    service = get_gmail_service()
    service.users().messages().trash(userId="me", id=msg_id).execute()
    click.echo(json.dumps({"status": "trashed", "id": msg_id}))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def untrash(msg_id: str):
    """Remove a message from trash."""
    service = get_gmail_service()
    service.users().messages().untrash(userId="me", id=msg_id).execute()
    click.echo(json.dumps({"status": "untrashed", "id": msg_id}))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def delete(msg_id: str):
    """Permanently delete a message (cannot be undone). Requires full scope."""
    from googleapiclient.errors import HttpError
    service = get_gmail_service()
    try:
        service.users().messages().delete(userId="me", id=msg_id).execute()
        click.echo(json.dumps({"status": "deleted", "id": msg_id}))
    except HttpError as e:
        if e.resp.status == 403:
            click.echo(json.dumps({
                "error": "Permanent delete requires full mailbox scope",
                "hint": "Uncomment 'https://mail.google.com/' in auth.py and re-authenticate, or use 'trash' instead"
            }), err=True)
            sys.exit(1)
        raise


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def mark_read(msg_id: str):
    """Mark a message as read."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me", id=msg_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    click.echo(json.dumps({"status": "marked_read", "id": msg_id}))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def mark_unread(msg_id: str):
    """Mark a message as unread."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me", id=msg_id,
        body={"addLabelIds": ["UNREAD"]}
    ).execute()
    click.echo(json.dumps({"status": "marked_unread", "id": msg_id}))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def star(msg_id: str):
    """Star a message."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me", id=msg_id,
        body={"addLabelIds": ["STARRED"]}
    ).execute()
    click.echo(json.dumps({"status": "starred", "id": msg_id}))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
def unstar(msg_id: str):
    """Remove star from a message."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me", id=msg_id,
        body={"removeLabelIds": ["STARRED"]}
    ).execute()
    click.echo(json.dumps({"status": "unstarred", "id": msg_id}))


# === Labels ===

@cli.command()
def list_labels():
    """List all labels."""
    service = get_gmail_service()
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    output = [{"id": l["id"], "name": l["name"], "type": l.get("type", "")} for l in labels]
    click.echo(json.dumps({"labels": output, "count": len(output)}, indent=2))


@cli.command()
@click.option("--name", required=True, help="Label name to create")
def create_label(name: str):
    """Create a new label."""
    service = get_gmail_service()
    result = service.users().labels().create(
        userId="me",
        body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    ).execute()
    click.echo(json.dumps({"status": "created", "id": result["id"], "name": result["name"]}))


@cli.command()
@click.option("--id", "label_id", required=True, help="Label ID to delete")
def delete_label(label_id: str):
    """Delete a label."""
    service = get_gmail_service()
    service.users().labels().delete(userId="me", id=label_id).execute()
    click.echo(json.dumps({"status": "deleted", "id": label_id}))


@cli.command()
@click.option("--id", "msg_id", required=True, help="Message ID")
@click.option("--add", multiple=True, help="Label IDs to add")
@click.option("--remove", multiple=True, help="Label IDs to remove")
def modify_labels(msg_id: str, add: tuple, remove: tuple):
    """Add or remove labels from a message."""
    service = get_gmail_service()
    body = {}
    if add:
        body["addLabelIds"] = list(add)
    if remove:
        body["removeLabelIds"] = list(remove)
    
    result = service.users().messages().modify(userId="me", id=msg_id, body=body).execute()
    click.echo(json.dumps({"status": "modified", "id": msg_id, "labelIds": result.get("labelIds", [])}))


# === Threads ===

@cli.command()
@click.option("--id", "thread_id", required=True, help="Thread ID")
@click.option("--full", is_flag=True, help="Include full message bodies")
def get_thread(thread_id: str, full: bool):
    """Get all messages in a thread."""
    service = get_gmail_service()
    thread = service.users().threads().get(
        userId="me", id=thread_id,
        format="full" if full else "metadata",
        metadataHeaders=["From", "To", "Subject", "Date"] if not full else None,
    ).execute()
    
    messages = []
    for msg in thread.get("messages", []):
        if full:
            messages.append(format_message_full(msg))
        else:
            messages.append(format_message_summary(msg))
    
    click.echo(json.dumps({"thread_id": thread_id, "messages": messages, "count": len(messages)}, indent=2))


@cli.command()
@click.option("--id", "thread_id", required=True, help="Thread ID")
def archive_thread(thread_id: str):
    """Archive all messages in a thread."""
    service = get_gmail_service()
    service.users().threads().modify(
        userId="me", id=thread_id,
        body={"removeLabelIds": ["INBOX"]}
    ).execute()
    click.echo(json.dumps({"status": "archived", "thread_id": thread_id}))


@cli.command()
@click.option("--id", "thread_id", required=True, help="Thread ID")
def trash_thread(thread_id: str):
    """Move all messages in a thread to trash."""
    service = get_gmail_service()
    service.users().threads().trash(userId="me", id=thread_id).execute()
    click.echo(json.dumps({"status": "trashed", "thread_id": thread_id}))


# === Batch Operations ===

@cli.command()
@click.option("--query", "-q", required=True, help="Gmail search query")
@click.option("--limit", "-n", default=50, help="Max messages to process")
def batch_archive(query: str, limit: int):
    """Archive all messages matching a query."""
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
    messages = results.get("messages", [])
    
    for msg in messages:
        service.users().messages().modify(
            userId="me", id=msg["id"],
            body={"removeLabelIds": ["INBOX"]}
        ).execute()
    
    click.echo(json.dumps({"status": "archived", "count": len(messages)}))


@cli.command()
@click.option("--query", "-q", required=True, help="Gmail search query")
@click.option("--limit", "-n", default=50, help="Max messages to process")
def batch_trash(query: str, limit: int):
    """Trash all messages matching a query."""
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
    messages = results.get("messages", [])
    
    for msg in messages:
        service.users().messages().trash(userId="me", id=msg["id"]).execute()
    
    click.echo(json.dumps({"status": "trashed", "count": len(messages)}))


@cli.command()
@click.option("--query", "-q", required=True, help="Gmail search query")
@click.option("--limit", "-n", default=50, help="Max messages to process")
def batch_mark_read(query: str, limit: int):
    """Mark all messages matching a query as read."""
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
    messages = results.get("messages", [])
    
    for msg in messages:
        service.users().messages().modify(
            userId="me", id=msg["id"],
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    
    click.echo(json.dumps({"status": "marked_read", "count": len(messages)}))


# === Attachments ===

@cli.command()
@click.option("--message-id", required=True, help="Message ID containing the attachment")
@click.option("--attachment-id", required=True, help="Attachment ID to download")
@click.option("--output", "-o", help="Output file path (default: original filename in current dir)")
def download_attachment(message_id: str, attachment_id: str, output: Optional[str]):
    """Download an attachment from a message."""
    service = get_gmail_service()
    
    # Get attachment data
    attachment = service.users().messages().attachments().get(
        userId="me", messageId=message_id, id=attachment_id
    ).execute()
    
    data = base64.urlsafe_b64decode(attachment["data"])
    
    # Determine output path
    if not output:
        # Get original filename from message
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        attachments = get_attachments_info(msg.get("payload", {}))
        filename = "attachment"
        for att in attachments:
            if att["attachmentId"] == attachment_id:
                filename = att["filename"]
                break
        output = filename
    
    # Write file
    output_path = Path(output)
    output_path.write_bytes(data)
    
    click.echo(json.dumps({
        "status": "downloaded",
        "path": str(output_path.absolute()),
        "size": len(data),
    }, indent=2))


# === Filters ===

@cli.command()
def list_filters():
    """List all Gmail filters."""
    service = get_gmail_service()
    results = service.users().settings().filters().list(userId="me").execute()
    filters = results.get("filter", [])
    
    output = []
    for f in filters:
        output.append({
            "id": f["id"],
            "criteria": f.get("criteria", {}),
            "action": f.get("action", {}),
        })
    
    click.echo(json.dumps({"filters": output, "count": len(output)}, indent=2))


@cli.command()
@click.option("--id", "filter_id", required=True, help="Filter ID")
def get_filter(filter_id: str):
    """Get details of a specific filter."""
    service = get_gmail_service()
    result = service.users().settings().filters().get(userId="me", id=filter_id).execute()
    click.echo(json.dumps({
        "id": result["id"],
        "criteria": result.get("criteria", {}),
        "action": result.get("action", {}),
    }, indent=2))


@cli.command()
@click.option("--from", "from_addr", help="Filter emails from this address")
@click.option("--to", "to_addr", help="Filter emails to this address")
@click.option("--subject", help="Filter emails with this subject")
@click.option("--query", help="Filter using Gmail search query")
@click.option("--has-attachment", is_flag=True, help="Filter emails with attachments")
@click.option("--add-label", multiple=True, help="Label ID to add to matching emails")
@click.option("--remove-label", multiple=True, help="Label ID to remove from matching emails")
@click.option("--archive", is_flag=True, help="Archive matching emails (remove from INBOX)")
@click.option("--mark-read", is_flag=True, help="Mark matching emails as read")
@click.option("--star", is_flag=True, help="Star matching emails")
@click.option("--forward", help="Forward matching emails to this address")
def create_filter(from_addr: Optional[str], to_addr: Optional[str], subject: Optional[str],
                  query: Optional[str], has_attachment: bool, add_label: tuple, 
                  remove_label: tuple, archive: bool, mark_read: bool, star: bool,
                  forward: Optional[str]):
    """Create a new Gmail filter."""
    service = get_gmail_service()
    
    # Build criteria
    criteria = {}
    if from_addr:
        criteria["from"] = from_addr
    if to_addr:
        criteria["to"] = to_addr
    if subject:
        criteria["subject"] = subject
    if query:
        criteria["query"] = query
    if has_attachment:
        criteria["hasAttachment"] = True
    
    if not criteria:
        click.echo("Error: at least one filter criteria is required", err=True)
        sys.exit(1)
    
    # Build action
    action = {}
    add_labels = list(add_label)
    remove_labels = list(remove_label)
    
    if archive:
        remove_labels.append("INBOX")
    if mark_read:
        remove_labels.append("UNREAD")
    if star:
        add_labels.append("STARRED")
    if forward:
        action["forward"] = forward
    
    if add_labels:
        action["addLabelIds"] = add_labels
    if remove_labels:
        action["removeLabelIds"] = remove_labels
    
    if not action:
        click.echo("Error: at least one filter action is required", err=True)
        sys.exit(1)
    
    # Create filter
    result = service.users().settings().filters().create(
        userId="me",
        body={"criteria": criteria, "action": action}
    ).execute()
    
    click.echo(json.dumps({
        "status": "created",
        "id": result["id"],
        "criteria": result.get("criteria", {}),
        "action": result.get("action", {}),
    }, indent=2))


@cli.command()
@click.option("--id", "filter_id", required=True, help="Filter ID to delete")
def delete_filter(filter_id: str):
    """Delete a Gmail filter."""
    service = get_gmail_service()
    service.users().settings().filters().delete(userId="me", id=filter_id).execute()
    click.echo(json.dumps({"status": "deleted", "id": filter_id}))


if __name__ == "__main__":
    cli()
