#!/usr/bin/env python3
"""Gmail CLI - read emails, create drafts, send messages."""

import base64
import json
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import click

from auth import get_gmail_service


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
    summary["body"] = decode_body(msg.get("payload", {}))
    summary["labelIds"] = msg.get("labelIds", [])
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
def draft(to_addr: Optional[str], cc: Optional[str], bcc: Optional[str], 
          subject: Optional[str], body: str, html: bool, reply_to: Optional[str]):
    """Create a draft email."""
    service = get_gmail_service()
    
    thread_id = None
    
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
    
    if html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "html"))
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
def send(draft_id: Optional[str], to_addr: Optional[str], cc: Optional[str],
         subject: Optional[str], body: Optional[str], html: bool):
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
        if html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "html"))
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


if __name__ == "__main__":
    cli()
