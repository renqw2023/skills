#!/bin/bash

# MediaWiki Health Check Script
# Comprehensive health check for MediaWiki instances

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

section() {
    echo ""
    echo "=== $* ==="
    echo ""
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
    cmd="$cmd --user-agent 'OpenClaw-MediaWiki-HealthCheck/1.0.0'"
    
    # Output control
    if [ "$DEBUG" = "true" ] || [ "$TRACE_API" = "true" ]; then
        cmd="$cmd --verbose"
    else
        cmd="$cmd --silent --show-error"
    fi
    
    echo "$cmd"
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================

# Check 1: Basic connectivity
check_connectivity() {
    section "1. Basic Connectivity"
    
    local url="$MEDIAWIKI_URL"
    info "Testing connection to: $url"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    if eval "$curl_cmd --head '$url' >/dev/null 2>&1"; then
        success "HTTP connectivity OK"
        return 0
    else
        error "Cannot connect to $url"
        return 1
    fi
}

# Check 2: API endpoint
check_api_endpoint() {
    section "2. API Endpoint"
    
    local api_url
    api_url=$(get_api_url)
    info "Testing API endpoint: $api_url"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=siteinfo&siprop=general&format=json' 2>&1") || {
        error "API endpoint not accessible"
        return 1
    }
    
    # Parse response
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        success "API endpoint accessible"
        
        # Extract info
        local site_name
        site_name=$(echo "$response" | jq -r '.query.general.sitename // empty')
        local version
        version=$(echo "$response" | jq -r '.query.general.generator // empty')
        local server
        server=$(echo "$response" | jq -r '.query.general.server // empty')
        
        if [ -n "$site_name" ]; then
            info "Site name: $site_name"
        fi
        if [ -n "$version" ]; then
            info "MediaWiki version: $version"
        fi
        if [ -n "$server" ]; then
            info "Server: $server"
        fi
        
        return 0
    else
        error "API returned invalid response"
        return 1
    fi
}

# Check 3: API functionality
check_api_functionality() {
    section "3. API Functionality"
    
    local api_url
    api_url=$(get_api_url)
    info "Testing API core functionality"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    # Test query action
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=tokens&type=login&format=json' 2>&1") || {
        error "API query action failed"
        return 1
    }
    
    local token
    token=$(echo "$response" | jq -r '.query.tokens.logintoken // empty')
    
    if [ -n "$token" ] && [ "$token" != "null" ]; then
        success "API functionality OK (login token available)"
        return 0
    else
        error "API missing login token functionality"
        return 1
    fi
}

# Check 4: Authentication
check_authentication() {
    section "4. Authentication"
    
    local api_url
    api_url=$(get_api_url)
    info "Testing authentication for user: $MEDIAWIKI_USERNAME"
    
    # Create temporary cookie file
    local cookie_file
    cookie_file=$(mktemp /tmp/mediawiki-healthcheck-cookies-XXXXXX)
    trap 'rm -f "$cookie_file"' EXIT
    
    # Get login token
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    curl_cmd="$curl_cmd --cookie-jar $cookie_file"
    
    local token_response
    token_response=$(eval "$curl_cmd '$api_url?action=query&meta=tokens&type=login&format=json' 2>&1") || {
        error "Failed to get login token"
        return 1
    }
    
    local token
    token=$(echo "$token_response" | jq -r '.query.tokens.logintoken // empty')
    token=$(echo "$token" | sed 's/\\\\//g')
    
    if [ -z "$token" ] || [ "$token" = "null" ]; then
        error "No login token received"
        return 1
    fi
    
    info "Login token obtained"
    
    # Perform login
    local login_response
    login_response=$(eval "$curl_cmd -X POST '$api_url' \
        --data-urlencode 'action=login' \
        --data-urlencode 'lgname=$MEDIAWIKI_USERNAME' \
        --data-urlencode 'lgpassword=$MEDIAWIKI_PASSWORD' \
        --data-urlencode 'lgtoken=$token' \
        --data-urlencode 'format=json' 2>&1") || {
        error "Login request failed"
        return 1
    }
    
    local login_result
    login_result=$(echo "$login_response" | jq -r '.login.result // empty')
    
    if [ "$login_result" = "Success" ]; then
        local user_id
        user_id=$(echo "$login_response" | jq -r '.login.lguserid // empty')
        success "Authentication successful!"
        info "User ID: $user_id"
        return 0
    else
        local reason
        reason=$(echo "$login_response" | jq -r '.login.reason // "Unknown error"')
        error "Authentication failed: $reason"
        return 1
    fi
}

# Check 5: User permissions
check_user_permissions() {
    section "5. User Permissions"
    
    local api_url
    api_url=$(get_api_url)
    
    # Use existing cookie file or create new one
    local cookie_file
    cookie_file=$(mktemp /tmp/mediawiki-permissions-cookies-XXXXXX)
    
    # First login
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    curl_cmd="$curl_cmd --cookie-jar $cookie_file --cookie $cookie_file"
    
    # Get token and login (simplified)
    local token_response
    token_response=$(eval "$curl_cmd '$api_url?action=query&meta=tokens&type=login&format=json'")
    local token
    token=$(echo "$token_response" | jq -r '.query.tokens.logintoken // empty')
    token=$(echo "$token" | sed 's/\\\\//g')
    
    eval "$curl_cmd -X POST '$api_url' \
        --data-urlencode 'action=login' \
        --data-urlencode 'lgname=$MEDIAWIKI_USERNAME' \
        --data-urlencode 'lgpassword=$MEDIAWIKI_PASSWORD' \
        --data-urlencode 'lgtoken=$token' \
        --data-urlencode 'format=json' >/dev/null 2>&1"
    
    # Get user info
    local user_response
    user_response=$(eval "$curl_cmd '$api_url?action=query&meta=userinfo&uiprop=rights|groups&format=json'") || {
        warn "Failed to get user permissions"
        rm -f "$cookie_file"
        return 1
    }
    
    rm -f "$cookie_file"
    
    # Parse permissions
    local username
    username=$(echo "$user_response" | jq -r '.query.userinfo.name // empty')
    
    if [ -z "$username" ] || [ "$username" = "null" ]; then
        warn "Unable to retrieve user information"
        return 1
    fi
    
    success "User: $username"
    
    # Check groups
    local groups
    groups=$(echo "$user_response" | jq -r '.query.userinfo.groups[]? | select(. != "*")' 2>/dev/null)
    
    if [ -n "$groups" ]; then
        info "Groups:"
        echo "$groups" | while read group; do
            echo "  • $group"
        done
    else
        info "No specific groups (user may only have implicit '*' group)"
    fi
    
    # Check important rights
    local rights
    rights=$(echo "$user_response" | jq -r '.query.userinfo.rights[]?' 2>/dev/null)
    
    local important_rights=("edit" "writeapi" "createpage" "upload" "delete" "move")
    local has_important=false
    
    for right in "${important_rights[@]}"; do
        if echo "$rights" | grep -q "^$right$"; then
            success "  ✓ Has right: $right"
            has_important=true
        fi
    done
    
    if [ "$has_important" = "false" ]; then
        warn "  No important rights found"
    fi
    
    return 0
}

# Check 6: Performance
check_performance() {
    section "6. Performance"
    
    local api_url
    api_url=$(get_api_url)
    info "Testing API response time"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    # Measure response time
    local start_time
    start_time=$(date +%s%3N)
    
    eval "$curl_cmd '$api_url?action=query&meta=siteinfo&format=json' >/dev/null 2>&1"
    
    local end_time
    end_time=$(date +%s%3N)
    local response_time=$((end_time - start_time))
    
    if [ "$response_time" -lt 1000 ]; then
        success "Response time: ${response_time}ms (excellent)"
    elif [ "$response_time" -lt 3000 ]; then
        info "Response time: ${response_time}ms (good)"
    elif [ "$response_time" -lt 5000 ]; then
        warn "Response time: ${response_time}ms (slow)"
    else
        warn "Response time: ${response_time}ms (very slow)"
    fi
    
    return 0
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

main() {
    echo ""
    echo "========================================="
    echo "    MediaWiki Health Check"
    echo "========================================="
    echo ""
    echo "Wiki URL: $MEDIAWIKI_URL"
    echo "Username: $MEDIAWIKI_USERNAME"
    echo "API Path: $MEDIAWIKI_API_PATH"
    echo "Start Time: $(date)"
    echo ""
    
    # Run all checks
    local passed=0
    local total=0
    local failed_checks=()
    
    # Check 1: Connectivity
    total=$((total + 1))
    if check_connectivity; then
        passed=$((passed + 1))
    else
        failed_checks+=("Connectivity")
    fi
    
    # Check 2: API Endpoint
    total=$((total + 1))
    if check_api_endpoint; then
        passed=$((passed + 1))
    else
        failed_checks+=("API Endpoint")
    fi
    
    # Check 3: API Functionality
    total=$((total + 1))
    if check_api_functionality; then
        passed=$((passed + 1))
    else
        failed_checks+=("API Functionality")
    fi
    
    # Check 4: Authentication
    total=$((total + 1))
    if check_authentication; then
        passed=$((passed + 1))
    else
        failed_checks+=("Authentication")
    fi
    
    # Check 5: User Permissions
    total=$((total + 1))
    if check_user_permissions; then
        passed=$((passed + 1))
    else
        failed_checks+=("User Permissions")
    fi
    
    # Check 6: Performance
    total=$((total + 1))
    if check_performance; then
        passed=$((passed + 1))
    else
        failed_checks+=("Performance")
    fi
    
    # Summary
    section "Health Check Summary"
    
    echo "Checks passed: $passed/$total"
    echo ""
    
    if [ ${#failed_checks[@]} -gt 0 ]; then
        echo "Failed checks:"
        for check in "${failed_checks[@]}"; do
            echo "  • $check"
        done
        echo ""
    fi
    
    # Overall status
    if [ "$passed" -eq "$total" ]; then
        success "ALL CHECKS PASSED! MediaWiki instance is healthy and fully functional."
        echo ""
        info "The wiki is ready for use with all tested functionality."
    elif [ "$passed" -ge $((total * 3 / 4)) ]; then
        warn "MOST CHECKS PASSED ($passed/$total). The wiki is functional but has some issues."
        echo ""
        info "Review the failed checks above for specific issues."
    elif [ "$passed" -ge $((total / 2)) ]; then
        error "PARTIAL FUNCTIONALITY ($passed/$total). The wiki has significant issues."
        echo ""
        info "Some core functionality may not work correctly."
    else
        error "CRITICAL ISSUES ($passed/$total). The wiki is not functional."
        echo ""
        info "Immediate attention is required for the failed checks."
    fi
    
    # Recommendations
    section "Recommendations"
    
    if [ ${#failed_checks[@]} -gt 0 ]; then
        echo "Based on the failed checks, consider:"
        echo ""
        
        for check in "${failed_checks[@]}"; do
            case "$check" in
                "Connectivity")
                    echo "  • Check network connectivity and firewall settings"
                    echo "  • Verify the wiki URL is correct"
                    ;;
                "API Endpoint")
                    echo "  • Verify the API path (/w/api.php or /api.php)"
                    echo "  • Check if the wiki is properly installed"
                    ;;
                "API Functionality")
                    echo "  • Check MediaWiki API configuration"
                    echo "  • Verify the wiki is not in maintenance mode"
                    ;;
                "Authentication")
                    echo "  • Verify username and password"
                    echo "  • Check if the user account is active"
                    echo "  • Ensure the user has login permissions"
                    ;;
                "User Permissions")
                    echo "  • Check user group assignments"
                    echo "  • Verify the user has necessary rights"
                    ;;
                "Performance")
                    echo "  • Check server load and resources"
                    echo "  • Consider optimizing the wiki"
                    ;;
            esac
        done
    else
        echo "No specific recommendations. The wiki appears to be in good health."
    fi
    
    echo ""
    echo "End Time: $(date)"
    echo "========================================="
    
    # Return code
    if [ "$passed" -eq "$total" ]; then
        return 0
    else
        return 1
    fi
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
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --debug     Enable debug output"
            echo "  --trace     Enable API tracing"
            echo "  --config    Specify configuration file"
            echo "  --help      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Run main function
main "$@"