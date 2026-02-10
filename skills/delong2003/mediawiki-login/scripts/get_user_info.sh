#!/bin/bash

# MediaWiki User Information Script
# Retrieves detailed user information after login

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load configuration
CONFIG_FILE="${MEDIAWIKI_CONFIG:-./config/mediawiki-config.sh}"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "ERROR: Configuration file not found: $CONFIG_FILE" >&2
    echo "Please copy config/mediawiki-config-template.sh to config/mediawiki-config.sh and edit with your credentials" >&2
    exit 1
fi

# Set defaults
: ${MEDIAWIKI_URL:?"ERROR: MEDIAWIKI_URL not set. Please configure in $CONFIG_FILE"}
: ${MEDIAWIKI_API_PATH:=/w/api.php}
: ${MEDIAWIKI_TIMEOUT:=30}
: ${DEBUG:=false}
: ${TRACE_API:=false}
: ${MEDIAWIKI_COOKIE_FILE:=""}

# ============================================================================
# FUNCTIONS
# ============================================================================

log() {
    if [ "$DEBUG" = "true" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
    fi
}

error() {
    echo "❌ ERROR: $*" >&2
    exit 1
}

success() {
    echo "✅ $*"
}

info() {
    echo "ℹ️  $*"
}

warn() {
    echo "⚠️  WARNING: $*" >&2
}

# Get API URL
get_api_url() {
    echo "${MEDIAWIKI_URL}${MEDIAWIKI_API_PATH}"
}

# Get curl command with options
get_curl_cmd() {
    local cmd="curl"
    
    # Basic options
    cmd="$cmd --max-time ${MEDIAWIKI_TIMEOUT}"
    cmd="$cmd --fail"  # Fail on HTTP errors
    
    # Cookie handling if file exists
    if [ -n "$MEDIAWIKI_COOKIE_FILE" ] && [ -f "$MEDIAWIKI_COOKIE_FILE" ]; then
        cmd="$cmd --cookie ${MEDIAWIKI_COOKIE_FILE}"
        log "Using cookie file: $MEDIAWIKI_COOKIE_FILE"
    else
        warn "No cookie file specified. Using anonymous access."
    fi
    
    # SSL verification
    if [ "${MEDIAWIKI_VERIFY_SSL:-true}" = "false" ]; then
        cmd="$cmd --insecure"
        log "SSL verification disabled"
    fi
    
    # Proxy if set
    if [ -n "${MEDIAWIKI_PROXY:-}" ]; then
        cmd="$cmd --proxy ${MEDIAWIKI_PROXY}"
        log "Using proxy: ${MEDIAWIKI_PROXY}"
    fi
    
    # User agent
    cmd="$cmd --user-agent 'OpenClaw-MediaWiki-Login/1.0.0'"
    
    # Output control
    if [ "$DEBUG" = "true" ] || [ "$TRACE_API" = "true" ]; then
        cmd="$cmd --verbose"
    else
        cmd="$cmd --silent --show-error"
    fi
    
    echo "$cmd"
}

# Check if user is logged in
check_login_status() {
    local api_url
    api_url=$(get_api_url)
    log "Checking login status"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=userinfo&format=json' 2>&1") || {
        error "Failed to check login status"
    }
    
    local is_anonymous
    is_anonymous=$(echo "$response" | jq -r '.query.userinfo.anon // empty')
    local username
    username=$(echo "$response" | jq -r '.query.userinfo.name // empty')
    
    if [ -n "$is_anonymous" ]; then
        echo "anonymous"
        return 0
    elif [ -n "$username" ] && [ "$username" != "null" ]; then
        echo "$username"
        return 0
    else
        echo "unknown"
        return 1
    fi
}

# Get detailed user information
get_user_info() {
    local api_url
    api_url=$(get_api_url)
    
    log "Getting detailed user information"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    # Get comprehensive user info
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=userinfo&uiprop=rights|groups|options|editcount|realname|email|registrationdate&format=json' 2>&1") || {
        error "Failed to get user information"
    }
    
    # Check if response is valid JSON
    if ! echo "$response" | jq -e . >/dev/null 2>&1; then
        error "Invalid JSON response from API"
    fi
    
    echo "$response"
}

# Parse and display user information
display_user_info() {
    local response="$1"
    
    echo ""
    echo "=== User Information ==="
    echo ""
    
    # Basic info
    local user_id
    user_id=$(echo "$response" | jq -r '.query.userinfo.id // empty')
    local username
    username=$(echo "$response" | jq -r '.query.userinfo.name // empty')
    
    if [ -n "$user_id" ] && [ "$user_id" != "null" ]; then
        success "User ID: $user_id"
    fi
    
    if [ -n "$username" ] && [ "$username" != "null" ]; then
        success "Username: $username"
    else
        info "Not logged in (anonymous user)"
        return 1
    fi
    
    # Edit count
    local edit_count
    edit_count=$(echo "$response" | jq -r '.query.userinfo.editcount // empty')
    if [ -n "$edit_count" ] && [ "$edit_count" != "null" ]; then
        info "Edit count: $edit_count"
    fi
    
    # Real name (if available)
    local realname
    realname=$(echo "$response" | jq -r '.query.userinfo.realname // empty')
    if [ -n "$realname" ] && [ "$realname" != "null" ]; then
        info "Real name: $realname"
    fi
    
    # Registration date
    local registration
    registration=$(echo "$response" | jq -r '.query.userinfo.registrationdate // empty')
    if [ -n "$registration" ] && [ "$registration" != "null" ]; then
        info "Registered: $registration"
    fi
    
    # Groups
    echo ""
    echo "=== Groups ==="
    local groups
    groups=$(echo "$response" | jq -r '.query.userinfo.groups[]? | select(. != "*")' 2>/dev/null)
    
    if [ -n "$groups" ]; then
        echo "$groups" | while read group; do
            echo "  • $group"
        done
    else
        info "No groups found (user may only have implicit '*' group)"
    fi
    
    # Rights
    echo ""
    echo "=== Rights ==="
    local rights
    rights=$(echo "$response" | jq -r '.query.userinfo.rights[]?' 2>/dev/null)
    
    if [ -n "$rights" ]; then
        local count=0
        echo "$rights" | while read right; do
            count=$((count + 1))
            if [ $count -le 20 ]; then
                echo "  • $right"
            fi
        done
        
        local total_count
        total_count=$(echo "$rights" | wc -l)
        if [ $total_count -gt 20 ]; then
            info "... and $((total_count - 20)) more rights"
        fi
        info "Total rights: $total_count"
    else
        info "No specific rights found"
    fi
    
    # Options (user preferences)
    echo ""
    echo "=== User Options ==="
    local options
    options=$(echo "$response" | jq -r '.query.userinfo.options | to_entries[] | "\(.key): \(.value)"' 2>/dev/null)
    
    if [ -n "$options" ]; then
        echo "$options" | head -10 | while read option; do
            echo "  • $option"
        done
        
        local options_count
        options_count=$(echo "$options" | wc -l)
        if [ $options_count -gt 10 ]; then
            info "... and $((options_count - 10)) more options"
        fi
    else
        info "No user options retrieved"
    fi
    
    return 0
}

# Check user permissions for specific actions
check_permissions() {
    local response="$1"
    
    echo ""
    echo "=== Permission Check ==="
    
    local rights
    rights=$(echo "$response" | jq -r '.query.userinfo.rights[]?' 2>/dev/null)
    
    # Define important permissions to check
    local important_permissions=(
        "edit"
        "createpage"
        "createtalk"
        "writeapi"
        "editprotected"
        "delete"
        "upload"
        "move"
        "block"
        "protect"
        "rollback"
        "browsearchive"
    )
    
    local has_any=false
    for perm in "${important_permissions[@]}"; do
        if echo "$rights" | grep -q "^$perm$"; then
            success "  ✓ $perm"
            has_any=true
        fi
    done
    
    if [ "$has_any" = "false" ]; then
        warn "  No important permissions found"
    fi
}

# Display API limits and warnings
display_api_info() {
    local response="$1"
    
    echo ""
    echo "=== API Information ==="
    
    # Check for warnings
    local warnings
    warnings=$(echo "$response" | jq -r '.warnings? | to_entries[] | "\(.key): \(.value)"' 2>/dev/null)
    
    if [ -n "$warnings" ]; then
        echo "$warnings" | while read warning; do
            warn "  $warning"
        done
    else
        info "  No API warnings"
    fi
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

main() {
    echo "=== MediaWiki User Information ==="
    echo "URL: $MEDIAWIKI_URL"
    echo "API Path: $MEDIAWIKI_API_PATH"
    
    if [ -n "$MEDIAWIKI_COOKIE_FILE" ] && [ -f "$MEDIAWIKI_COOKIE_FILE" ]; then
        info "Using cookie file: $MEDIAWIKI_COOKIE_FILE"
    fi
    
    echo ""
    
    # Step 1: Check login status
    echo "1. Checking login status..."
    local status
    status=$(check_login_status)
    
    case "$status" in
        anonymous)
            warn "Not logged in (anonymous access)"
            info "For detailed information, please login first:"
            info "  ./scripts/login.sh"
            ;;
        unknown)
            warn "Unable to determine login status"
            ;;
        *)
            success "Logged in as: $status"
            ;;
    esac
    
    # Step 2: Get user information
    echo ""
    echo "2. Retrieving user information..."
    local user_info
    user_info=$(get_user_info)
    
    # Step 3: Display information
    display_user_info "$user_info"
    
    # Step 4: Check permissions
    check_permissions "$user_info"
    
    # Step 5: Display API info
    display_api_info "$user_info"
    
    echo ""
    success "User information retrieved successfully!"
    
    # Export useful variables
    local user_id
    user_id=$(echo "$user_info" | jq -r '.query.userinfo.id // empty')
    if [ -n "$user_id" ] && [ "$user_id" != "null" ]; then
        echo ""
        echo "=== Export Variables ==="
        echo "To use in other scripts:"
        echo "  export MEDIAWIKI_USER_ID=\"$user_id\""
        echo "  export MEDIAWIKI_USERNAME=\"$status\""
        echo "  export MEDIAWIKI_COOKIE_FILE=\"$MEDIAWIKI_COOKIE_FILE\""
    fi
    
    return 0
}

# ============================================================================
# EXECUTION
# ============================================================================

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            export DEBUG=true
            shift
            ;;
        --trace)
            export TRACE_API=true
            export DEBUG=true
            shift
            ;;
        --config)
            export MEDIAWIKI_CONFIG="$2"
            shift 2
            ;;
        --cookie-file)
            export MEDIAWIKI_COOKIE_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --debug             Enable debug output"
            echo "  --trace             Enable API tracing"
            echo "  --config FILE       Specify configuration file"
            echo "  --cookie-file FILE  Specify cookie file location"
            echo "  --help              Show this help"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Run main function
main "$@"