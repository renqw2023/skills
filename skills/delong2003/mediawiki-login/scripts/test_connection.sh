#!/bin/bash

# MediaWiki Connection Test Script
# Tests basic connectivity to MediaWiki API without authentication

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
    cmd="$cmd --user-agent 'OpenClaw-MediaWiki-Login/1.0.0'"
    
    # Output control
    if [ "$DEBUG" = "true" ] || [ "$TRACE_API" = "true" ]; then
        cmd="$cmd --verbose"
    else
        cmd="$cmd --silent --show-error"
    fi
    
    echo "$cmd"
}

# Test basic HTTP connectivity
test_http_connectivity() {
    local url="$MEDIAWIKI_URL"
    log "Testing HTTP connectivity to: $url"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    if eval "$curl_cmd --head '$url' >/dev/null 2>&1"; then
        success "HTTP connectivity OK"
        return 0
    else
        error "Cannot connect to $url. Check URL, network, and firewall settings."
    fi
}

# Test API endpoint
test_api_endpoint() {
    local api_url
    api_url=$(get_api_url)
    log "Testing API endpoint: $api_url"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=siteinfo&siprop=general&format=json' 2>&1") || {
        error "API endpoint not accessible. Check API path. Tried: $api_url"
    }
    
    # Check if response contains valid JSON
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        success "API endpoint accessible"
        
        # Extract site name
        local site_name
        site_name=$(echo "$response" | jq -r '.query.general.sitename // empty')
        if [ -n "$site_name" ]; then
            info "Site: $site_name"
        fi
        
        # Extract server URL
        local server_url
        server_url=$(echo "$response" | jq -r '.query.general.server // empty')
        if [ -n "$server_url" ]; then
            info "Server: $server_url"
        fi
        
        # Extract MediaWiki version
        local version
        version=$(echo "$response" | jq -r '.query.general.generator // empty')
        if [ -n "$version" ]; then
            info "Version: $version"
        fi
        
        return 0
    else
        error "API returned invalid response. Check API path. Response: ${response:0:200}"
    fi
}

# Test API functionality
test_api_functionality() {
    local api_url
    api_url=$(get_api_url)
    log "Testing API functionality"
    
    local curl_cmd
    curl_cmd=$(get_curl_cmd)
    
    # Test query action
    local response
    response=$(eval "$curl_cmd '$api_url?action=query&meta=tokens&type=login&format=json' 2>&1") || {
        error "API query action failed"
    }
    
    if echo "$response" | jq -e '.query.tokens.logintoken' >/dev/null 2>&1; then
        success "API functionality OK (login token available)"
        return 0
    else
        error "API missing required functionality. Response: ${response:0:200}"
    fi
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

main() {
    echo "=== MediaWiki Connection Test ==="
    echo "URL: $MEDIAWIKI_URL"
    echo "API Path: $MEDIAWIKI_API_PATH"
    echo ""
    
    # Create temporary cookie file if not set
    if [ -z "${MEDIAWIKI_COOKIE_FILE:-}" ]; then
        export MEDIAWIKI_COOKIE_FILE="$(mktemp /tmp/mediawiki-cookies-XXXXXX)"
        trap 'rm -f "$MEDIAWIKI_COOKIE_FILE"' EXIT
        log "Using temporary cookie file: $MEDIAWIKI_COOKIE_FILE"
    fi
    
    # Run tests
    local tests_passed=0
    local tests_total=0
    
    # Test 1: HTTP connectivity
    echo "1. Testing HTTP connectivity..."
    if test_http_connectivity; then
        tests_passed=$((tests_passed + 1))
    fi
    tests_total=$((tests_total + 1))
    
    # Test 2: API endpoint
    echo ""
    echo "2. Testing API endpoint..."
    if test_api_endpoint; then
        tests_passed=$((tests_passed + 1))
    fi
    tests_total=$((tests_total + 1))
    
    # Test 3: API functionality
    echo ""
    echo "3. Testing API functionality..."
    if test_api_functionality; then
        tests_passed=$((tests_passed + 1))
    fi
    tests_total=$((tests_total + 1))
    
    # Summary
    echo ""
    echo "=== Test Summary ==="
    echo "Tests passed: $tests_passed/$tests_total"
    
    if [ "$tests_passed" -eq "$tests_total" ]; then
        success "All connection tests passed! MediaWiki instance is ready for authentication."
        echo ""
        echo "Next steps:"
        echo "1. Run ./scripts/login.sh to authenticate"
        echo "2. Run ./scripts/health_check.sh for comprehensive testing"
        return 0
    else
        error "Connection tests failed. Please check configuration and network settings."
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
            error "Unknown option: $1"
            ;;
    esac
done

# Run main function
main "$@"