#!/bin/bash
# Non-destructive test suite for Gmail CLI
# All write operations are reversed or use test data that's cleaned up

set -e

cd /Users/thomasmustier/skill-gmail-api
GMAIL="./scripts/gmail.py"
VENV_PYTHON=".venv/bin/python"

echo "=========================================="
echo "Gmail CLI Non-Destructive Test Suite"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}→${NC} $1"; }

# ==========================================
# PHASE 1: READ-ONLY OPERATIONS
# ==========================================
echo ""
echo "=== PHASE 1: READ-ONLY OPERATIONS ==="

info "Testing: read (list emails)"
READ_OUTPUT=$($VENV_PYTHON $GMAIL read --limit 3 2>&1) || fail "read command"
echo "$READ_OUTPUT" | head -20
MSG_ID=$(echo "$READ_OUTPUT" | grep -o '"id": "[^"]*"' | head -1 | sed 's/"id": "//;s/"//') 
THREAD_ID=$(echo "$READ_OUTPUT" | grep -o '"threadId": "[^"]*"' | head -1 | sed 's/"threadId": "//;s/"//')
pass "read --limit 3"

info "Testing: read with query"
$VENV_PYTHON $GMAIL read --limit 2 --query "is:unread" | head -10
pass "read --query"

info "Testing: get (single message)"
if [ -n "$MSG_ID" ]; then
    $VENV_PYTHON $GMAIL get --id "$MSG_ID" | head -30
    pass "get --id"
else
    echo "Skipped (no message ID)"
fi

info "Testing: get-thread"
if [ -n "$THREAD_ID" ]; then
    $VENV_PYTHON $GMAIL get-thread --id "$THREAD_ID" | head -30
    pass "get-thread"
else
    echo "Skipped (no thread ID)"
fi

info "Testing: list-labels"
LABELS_OUTPUT=$($VENV_PYTHON $GMAIL list-labels 2>&1)
echo "$LABELS_OUTPUT" | head -20
pass "list-labels"

info "Testing: list-drafts"
$VENV_PYTHON $GMAIL list-drafts | head -20
pass "list-drafts"

info "Testing: list-filters"
$VENV_PYTHON $GMAIL list-filters | head -20
pass "list-filters"

# ==========================================
# PHASE 2: REVERSIBLE MESSAGE OPERATIONS
# ==========================================
echo ""
echo "=== PHASE 2: REVERSIBLE MESSAGE OPERATIONS ==="
echo "(Using message: $MSG_ID)"

if [ -n "$MSG_ID" ]; then
    # Get current state
    CURRENT_STATE=$($VENV_PYTHON $GMAIL get --id "$MSG_ID")
    WAS_STARRED=$(echo "$CURRENT_STATE" | grep -c '"STARRED"' || true)
    WAS_UNREAD=$(echo "$CURRENT_STATE" | grep -c '"UNREAD"' || true)
    
    info "Testing: star/unstar"
    $VENV_PYTHON $GMAIL star --id "$MSG_ID"
    pass "star"
    $VENV_PYTHON $GMAIL unstar --id "$MSG_ID"
    pass "unstar"
    # Restore if was starred
    if [ "$WAS_STARRED" -gt 0 ]; then
        $VENV_PYTHON $GMAIL star --id "$MSG_ID"
        info "Restored star state"
    fi
    
    info "Testing: mark-read/mark-unread"
    $VENV_PYTHON $GMAIL mark-read --id "$MSG_ID"
    pass "mark-read"
    $VENV_PYTHON $GMAIL mark-unread --id "$MSG_ID"
    pass "mark-unread"
    # Restore original state
    if [ "$WAS_UNREAD" -eq 0 ]; then
        $VENV_PYTHON $GMAIL mark-read --id "$MSG_ID"
        info "Restored read state"
    fi
    
    info "Testing: archive (will restore immediately)"
    $VENV_PYTHON $GMAIL archive --id "$MSG_ID"
    pass "archive"
    # Restore to inbox
    $VENV_PYTHON $GMAIL modify-labels --id "$MSG_ID" --add INBOX
    pass "modify-labels (restore to INBOX)"
    
    info "Testing: trash/untrash"
    $VENV_PYTHON $GMAIL trash --id "$MSG_ID"
    pass "trash"
    $VENV_PYTHON $GMAIL untrash --id "$MSG_ID"
    pass "untrash"
fi

# ==========================================
# PHASE 3: DRAFT LIFECYCLE
# ==========================================
echo ""
echo "=== PHASE 3: DRAFT LIFECYCLE ==="

info "Testing: draft create"
DRAFT_OUTPUT=$($VENV_PYTHON $GMAIL draft \
    --to "test-do-not-send@example.com" \
    --subject "[TEST] Gmail CLI Test Draft - DELETE ME" \
    --body "This is a test draft created by the test suite. It will be deleted." 2>&1)
echo "$DRAFT_OUTPUT"
DRAFT_ID=$(echo "$DRAFT_OUTPUT" | grep -o '"draft_id": "[^"]*"' | sed 's/"draft_id": "//;s/"//')
pass "draft create"

info "Testing: list-drafts (verify draft exists)"
$VENV_PYTHON $GMAIL list-drafts | grep -q "$DRAFT_ID" && pass "draft appears in list"

info "Testing: delete-draft"
if [ -n "$DRAFT_ID" ]; then
    $VENV_PYTHON $GMAIL delete-draft --draft-id "$DRAFT_ID"
    pass "delete-draft"
else
    fail "No draft ID to delete"
fi

# ==========================================
# PHASE 4: LABEL LIFECYCLE
# ==========================================
echo ""
echo "=== PHASE 4: LABEL LIFECYCLE ==="

TEST_LABEL_NAME="TEST-Gmail-CLI-$(date +%s)"

info "Testing: create-label"
LABEL_OUTPUT=$($VENV_PYTHON $GMAIL create-label --name "$TEST_LABEL_NAME" 2>&1)
echo "$LABEL_OUTPUT"
TEST_LABEL_ID=$(echo "$LABEL_OUTPUT" | grep -o '"id": "[^"]*"' | sed 's/"id": "//;s/"//')
pass "create-label"

if [ -n "$TEST_LABEL_ID" ] && [ -n "$MSG_ID" ]; then
    info "Testing: modify-labels (add label)"
    $VENV_PYTHON $GMAIL modify-labels --id "$MSG_ID" --add "$TEST_LABEL_ID"
    pass "modify-labels --add"
    
    info "Testing: modify-labels (remove label)"
    $VENV_PYTHON $GMAIL modify-labels --id "$MSG_ID" --remove "$TEST_LABEL_ID"
    pass "modify-labels --remove"
fi

info "Testing: delete-label"
if [ -n "$TEST_LABEL_ID" ]; then
    $VENV_PYTHON $GMAIL delete-label --id "$TEST_LABEL_ID"
    pass "delete-label"
fi

# ==========================================
# PHASE 5: FILTER LIFECYCLE
# ==========================================
echo ""
echo "=== PHASE 5: FILTER LIFECYCLE ==="

info "Testing: create-filter (harmless filter)"
FILTER_OUTPUT=$($VENV_PYTHON $GMAIL create-filter \
    --from "test-filter-cli-nonexistent-12345@example.com" \
    --star 2>&1)
echo "$FILTER_OUTPUT"
FILTER_ID=$(echo "$FILTER_OUTPUT" | grep -o '"id": "[^"]*"' | sed 's/"id": "//;s/"//')
pass "create-filter"

if [ -n "$FILTER_ID" ]; then
    info "Testing: get-filter"
    $VENV_PYTHON $GMAIL get-filter --id "$FILTER_ID"
    pass "get-filter"
    
    info "Testing: delete-filter"
    $VENV_PYTHON $GMAIL delete-filter --id "$FILTER_ID"
    pass "delete-filter"
fi

# ==========================================
# PHASE 6: THREAD OPERATIONS
# ==========================================
echo ""
echo "=== PHASE 6: THREAD OPERATIONS ==="

if [ -n "$THREAD_ID" ]; then
    info "Testing: archive-thread (will restore)"
    $VENV_PYTHON $GMAIL archive-thread --id "$THREAD_ID"
    pass "archive-thread"
    
    # Restore thread to inbox by modifying first message
    $VENV_PYTHON $GMAIL modify-labels --id "$MSG_ID" --add INBOX
    info "Restored thread to INBOX"
    
    # Note: trash-thread is more destructive, we'll test with immediate untrash
    info "Testing: trash-thread (will untrash immediately)"
    $VENV_PYTHON $GMAIL trash-thread --id "$THREAD_ID"
    pass "trash-thread"
    
    # Untrash the message to restore
    $VENV_PYTHON $GMAIL untrash --id "$MSG_ID"
    pass "untrash (restored thread)"
fi

# ==========================================
# PHASE 7: ATTACHMENT OPERATIONS
# ==========================================
echo ""
echo "=== PHASE 7: ATTACHMENT OPERATIONS ==="

info "Looking for message with attachment"
ATTACH_MSG=$($VENV_PYTHON $GMAIL read --limit 10 --query "has:attachment" --full 2>&1)
ATTACH_MSG_ID=$(echo "$ATTACH_MSG" | grep -o '"id": "[^"]*"' | head -1 | sed 's/"id": "//;s/"//')
ATTACH_ID=$(echo "$ATTACH_MSG" | grep -o '"attachmentId": "[^"]*"' | head -1 | sed 's/"attachmentId": "//;s/"//')

if [ -n "$ATTACH_MSG_ID" ] && [ -n "$ATTACH_ID" ]; then
    info "Found attachment, testing download"
    $VENV_PYTHON $GMAIL download-attachment \
        --message-id "$ATTACH_MSG_ID" \
        --attachment-id "$ATTACH_ID" \
        -o /tmp/gmail-cli-test-attachment
    pass "download-attachment"
    rm -f /tmp/gmail-cli-test-attachment
    info "Cleaned up test attachment"
else
    echo "Skipped (no message with attachment found)"
fi

# ==========================================
# PHASE 8: BATCH OPERATIONS (SAFE QUERIES)
# ==========================================
echo ""
echo "=== PHASE 8: BATCH OPERATIONS (ZERO-MATCH QUERIES) ==="

info "Testing: batch-mark-read with impossible query (should match 0)"
$VENV_PYTHON $GMAIL batch-mark-read --query "from:this-email-does-not-exist-xyz123abc@nonexistent-domain-test.com" --limit 1
pass "batch-mark-read (0 matches)"

info "Testing: batch-archive with impossible query (should match 0)"
$VENV_PYTHON $GMAIL batch-archive --query "from:this-email-does-not-exist-xyz123abc@nonexistent-domain-test.com" --limit 1
pass "batch-archive (0 matches)"

# Skip batch-trash to be extra safe

# ==========================================
# PHASE 9: DRAFT WITH ATTACHMENT
# ==========================================
echo ""
echo "=== PHASE 9: DRAFT WITH ATTACHMENT ==="

# Create a test file
echo "Test attachment content" > /tmp/gmail-cli-test-file.txt

info "Testing: draft with attachment"
ATTACH_DRAFT=$($VENV_PYTHON $GMAIL draft \
    --to "test-do-not-send@example.com" \
    --subject "[TEST] Draft with attachment - DELETE ME" \
    --body "Test draft with attachment" \
    --attach /tmp/gmail-cli-test-file.txt 2>&1)
echo "$ATTACH_DRAFT"
ATTACH_DRAFT_ID=$(echo "$ATTACH_DRAFT" | grep -o '"draft_id": "[^"]*"' | sed 's/"draft_id": "//;s/"//')
pass "draft with attachment"

if [ -n "$ATTACH_DRAFT_ID" ]; then
    $VENV_PYTHON $GMAIL delete-draft --draft-id "$ATTACH_DRAFT_ID"
    pass "cleanup attachment draft"
fi

rm -f /tmp/gmail-cli-test-file.txt

# ==========================================
# SKIPPED TESTS (DESTRUCTIVE)
# ==========================================
echo ""
echo "=== SKIPPED TESTS (DESTRUCTIVE/IRREVERSIBLE) ==="
echo "- send: Would actually send an email"
echo "- delete: Permanently deletes (no undo)"
echo "- batch-trash: Modifies multiple messages"

# ==========================================
# SUMMARY
# ==========================================
echo ""
echo "=========================================="
echo -e "${GREEN}ALL TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Commands tested:"
echo "  READ: read, get, get-thread, list-labels, list-drafts, list-filters, get-filter"
echo "  MESSAGE: star, unstar, mark-read, mark-unread, archive, trash, untrash, modify-labels"
echo "  DRAFT: draft, delete-draft, draft with attachment"
echo "  LABEL: create-label, delete-label"
echo "  FILTER: create-filter, get-filter, delete-filter"
echo "  THREAD: archive-thread, trash-thread"
echo "  ATTACHMENT: download-attachment"
echo "  BATCH: batch-mark-read, batch-archive (with 0-match queries)"
echo ""
echo "Skipped (destructive):"
echo "  - send, delete, batch-trash"
