#!/bin/bash

# MediaWiki Login Script
# Authenticates with MediaWiki and establishes a session

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
: ${MEDIAWIKI_USERNAME:?"ERROR: MEDIAWIKI_USERNAME not set. Please configure in $CONFIG_FILE"}
: ${MEDIAWIKI_PASSWORD:?"ERROR: MEDIAWIKI_PASSWORD not set. Please configure in $CONFIG_FILE"}
: ${MEDIAWIKI_API_PATH:=/w/api.php}
: ${MEDIAWIKI_TIMEOUT:=30}
: ${DEBUG:=false}
: ${TRACE_API:=false}
: ${MEDIAWIKI_COOKIE_FILE:="/tmp/mediawiki-cookies-$(date +%s).txt"}

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
    
    # Cookie handling
    cmd="$cmd --cookie-jar ${MEDIAWIKI_COOKIE_FILE}"
    cmd="$cmd --cookie ${MEDIAWIKI_COOKIE_FILE}"
    
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

# Clean up cookie file on exit
cleanup() {
    if [ "${PRESERVE_COOKIES:-false}" != "true" ] && [ -f "$MEDIAWIKI_COOKIE_FILE" ]; then
        log "Cleaning up cookie file: $MEDIAWIKI_COOKIE_FILE"
        rm -f "$MEDIAWIKI_COOKIE_FILE"
    fi
}
trap cleanup EXIT

# Get login token from MediaWiki
get_login_token() {
    local api_url
    api_url=$(get_api_url)
    log "Getting login token from $api_url"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=tokens&type=login&format=json' 2>&1") || {
        error "Failed to get login token. Check connection and API endpoint."
    }
    
    # Parse token from response
    local token
    token=$(echo "$response" | jq -r '.query.tokens.logintoken // empty')
    
    if [ -z "$token" ] || [ "$token" = "null" ]; then
        if [ "$DEBUG" = "true" ]; then
            error "No login token in response. Response: ${response:0:500}"
        else
            error "No login token in response. API may not be functioning correctly."
        fi
    fi
    
    # Token often contains +\\ which needs to be decoded
    token=$(echo "$token" | sed 's/\\\\//g')
    log "Got login token: ${token:0:20}..."
    
    echo "$token"
}

# Perform login with token
perform_login() {
    local token="$1"
    local api_url
    api_url=$(get_api_url)
    
    log "Performing login for user: $MEDIAWIKI_USERNAME"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    # Build login request
    local response
    response=$(eval "$curl_cmd -X POST '$api_url' \
        --data-urlencode 'action=login' \
        --data-urlencode 'lgname=$MEDIAWIKI_USERNAME' \
        --data-urlencode 'lgpassword=$MEDIAWIKI_PASSWORD' \
        --data-urlencode 'lgtoken=$token' \
        --data-urlencode 'format=json' 2>&1") || {
        error "Login request failed"
    }
    
    # Parse login response
    local login_result
    login_result=$(echo "$response" | jq -r '.login.result // empty')
    
    if [ -z "$login_result" ]; then
        if [ "$DEBUG" = "true" ]; then
            error "Invalid login response. Response: ${response:0:500}"
        else
            error "Invalid login response from server"
        fi
    fi
    
    if [ "$login_result" = "Success" ]; then
        local user_id
        user_id=$(echo "$response" | jq -r '.login.lguserid // empty')
        local username
        username=$(echo "$response" | jq -r '.login.lgusername // empty')
        
        success "Login successful!"
        info "User ID: $user_id"
        info "Username: $username"
        
        # Save user info for other scripts
        if [ -n "${MEDIAWIKI_SESSION_INFO:-}" ]; then
            echo "$user_id" > "${MEDIAWIKI_SESSION_INFO}.userid"
            echo "$username" > "${MEDIAWIKI_SESSION_INFO}.username"
            log "Session info saved to: ${MEDIAWIKI_SESSION_INFO}.*"
        fi
        
        return 0
    else
        local reason
        reason=$(echo "$response" | jq -r '.login.reason // "Unknown error"')
        error "Login failed: $reason"
    fi
}

# Verify login by getting user info
verify_login() {
    local api_url
    api_url=$(get_api_url)
    log "Verifying login session"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=userinfo&uiprop=rights|groups|options&format=json' 2>&1") || {
        warn "Failed to verify login session"
        return 1
    }
    
    local username
    username=$(echo "$response" | jq -r '.query.userinfo.name // empty')
    local user_id
    user_id=$(echo "$response" | jq -r '.query.userinfo.id // empty')
    
    if [ -n "$username" ] && [ "$username" != "null" ]; then
        success "Session verified: $username (ID: $user_id)"
        
        # Display groups if available
        local groups
        groups=$(echo "$response" | jq -r '.query.userinfo.groups[]? | select(. != "*")' 2>/dev/null | tr '\n' ', ' | sed 's/, $//')
        if [ -n "$groups" ]; then
            info "Groups: $groups"
        fi
        
        # Display rights if available
        local rights_count
        rights_count=$(echo "$response" | jq -r '.query.userinfo.rights | length' 2>/dev/null)
        if [ "$rights_count" -gt 0 ]; then
            info "Rights count: $rights_count"
        fi
        
        return 0
    else
        warn "Session verification failed - not logged in"
        return 1
    fi
}

# Display session information
show_session_info() {
    if [ -f "$MEDIAWIKI_COOKIE_FILE" ]; then
        local cookie_size
        cookie_size=$(wc -c < "$MEDIAWIKI_COOKIE_FILE")
        info "Cookie file: $MEDIAWIKI_COOKIE_FILE ($cookie_size bytes)"
        
        if [ "$DEBUG" = "true" ]; then
            log "Cookie file contents:"
            cat "$MEDIAWIKI_COOKIE_FILE" | while read line; do
                log "  $line"
            done
        fi
    else
        warn "No cookie file created"
    fi
    
    # Show next steps
    echo ""
    echo "=== Next Steps ==="
    echo "1. Use cookie file for subsequent requests:"
    echo "   export MEDIAWIKI_COOKIE_FILE=\"$MEDIAWIKI_COOKIE_FILE\""
    echo ""
    echo "2. Test user information:"
    echo "   ./scripts/get_user_info.sh"
    echo ""
    echo "3. Run health check:"
    echo "   ./scripts/health_check.sh"
    echo ""
    echo "4. To preserve cookies for later use:"
    echo "   export PRESERVE_COOKIES=true"
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

main() {
    echo "=== MediaWiki Login ==="
    echo "URL: $MEDIAWIKI_URL"
    echo "Username: $MEDIAWIKI_USERNAME"
    echo "API Path: $MEDIAWIKI_API_PATH"
    echo ""
    
    # Check if already logged in
    if [ -f "$MEDIAWIKI_COOKIE_FILE" ] && [ "$(wc -c < "$MEDIAWIKI_COOKIE_FILE")" -gt 0 ]; then
        warn "Cookie file already exists: $MEDIAWIKI_COOKIE_FILE"
        if verify_login; then
            info "Already logged in with existing session"
            show_session_info
            return 0
        else
            warn "Existing session invalid, continuing with new login"
        fi
    fi
    
    # Step 1: Get login token
    echo "1. Getting login token..."
    local login_token
    login_token=$(get_login_token) || exit 1
    
    # Step 2: Perform login
    echo ""
    echo "2. Logging in..."
    perform_login "$login_token" || exit 1
    
    # Step 3: Verify login
    echo ""
    echo "3. Verifying session..."
    verify_login || warn "Session verification had issues"
    
    # Step 4: Show session info
    echo ""
    show_session_info
    
    success "Login process completed successfully!"
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
        --preserve-cookies)
            export PRESERVE_COOKIES=true
            shift
            ;;
        --session-info)
            export MEDIAWIKI_SESSION_INFO="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --debug             Enable debug output"
            echo "  --trace             Enable API tracing"
            echo "  --config FILE       Specify configuration file"
            echo "  --cookie-file FILE  Specify cookie file location"
            echo "  --preserve-cookies  Don't delete cookie file on exit"
            echo "  --session-info PREFIX Save session info to files"
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