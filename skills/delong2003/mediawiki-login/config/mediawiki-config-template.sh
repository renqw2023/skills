#!/bin/bash

# MediaWiki Configuration Template
# Copy this file to config/mediawiki-config.sh and edit with your credentials
# WARNING: Never commit config/mediawiki-config.sh to version control!

# ============================================================================
# REQUIRED SETTINGS
# ============================================================================

# MediaWiki instance URL (with https://)
# Example: https://wiki.example.com
export MEDIAWIKI_URL=""

# Authentication credentials
export MEDIAWIKI_USERNAME=""
export MEDIAWIKI_PASSWORD=""

# API path
# Default for most MediaWiki installations: /w/api.php
# Some installations use: /api.php
export MEDIAWIKI_API_PATH="/w/api.php"

# ============================================================================
# OPTIONAL SETTINGS
# ============================================================================

# Timeout in seconds for API requests
export MEDIAWIKI_TIMEOUT="30"

# Debug mode (true/false)
# When true, scripts will output detailed information
export DEBUG="false"

# Trace API calls (true/false)
# When true, shows raw API requests and responses
export TRACE_API="false"

# Cookie file location
# If not set, scripts will create temporary files
# export MEDIAWIKI_COOKIE_FILE="/tmp/mediawiki-cookies.txt"

# Proxy settings (if needed)
# export MEDIAWIKI_PROXY="http://proxy.example.com:8080"

# SSL verification
# Set to "false" to disable SSL certificate verification (not recommended for production)
export MEDIAWIKI_VERIFY_SSL="true"

# ============================================================================
# ADVANCED SETTINGS
# ============================================================================

# User agent string for API requests
export MEDIAWIKI_USER_AGENT="OpenClaw-MediaWiki-Login/1.0.0"

# Retry settings for failed requests
export MEDIAWIKI_RETRY_COUNT="3"
export MEDIAWIKI_RETRY_DELAY="2"

# Cache settings (in seconds)
export MEDIAWIKI_CACHE_TTL="300"

# ============================================================================
# VALIDATION
# ============================================================================

# Function to validate configuration
validate_config() {
    local errors=0
    
    # Check required variables
    if [ -z "$MEDIAWIKI_URL" ]; then
        echo "ERROR: MEDIAWIKI_URL is not set" >&2
        errors=$((errors + 1))
    fi
    
    if [ -z "$MEDIAWIKI_USERNAME" ]; then
        echo "ERROR: MEDIAWIKI_USERNAME is not set" >&2
        errors=$((errors + 1))
    fi
    
    if [ -z "$MEDIAWIKI_PASSWORD" ]; then
        echo "ERROR: MEDIAWIKI_PASSWORD is not set" >&2
        errors=$((errors + 1))
    fi
    
    # Validate URL format
    if [[ ! "$MEDIAWIKI_URL" =~ ^https?:// ]]; then
        echo "ERROR: MEDIAWIKI_URL must start with http:// or https://" >&2
        errors=$((errors + 1))
    fi
    
    # Validate API path
    if [[ ! "$MEDIAWIKI_API_PATH" =~ ^/ ]]; then
        echo "ERROR: MEDIAWIKI_API_PATH must start with /" >&2
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        echo "Configuration validation failed with $errors error(s)" >&2
        return 1
    fi
    
    echo "Configuration validation passed"
    return 0
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Get full API URL
get_api_url() {
    echo "${MEDIAWIKI_URL}${MEDIAWIKI_API_PATH}"
}

# Get curl base command with common options
get_curl_cmd() {
    local cmd="curl"
    
    # Add timeout
    cmd="$cmd --max-time ${MEDIAWIKI_TIMEOUT}"
    
    # Add proxy if set
    if [ -n "$MEDIAWIKI_PROXY" ]; then
        cmd="$cmd --proxy ${MEDIAWIKI_PROXY}"
    fi
    
    # SSL verification
    if [ "$MEDIAWIKI_VERIFY_SSL" = "false" ]; then
        cmd="$cmd --insecure"
    fi
    
    # User agent
    cmd="$cmd --user-agent \"${MEDIAWIKI_USER_AGENT}\""
    
    # Silent mode unless debugging
    if [ "$DEBUG" != "true" ] && [ "$TRACE_API" != "true" ]; then
        cmd="$cmd --silent --show-error"
    fi
    
    echo "$cmd"
}

# ============================================================================
# OUTPUT CURRENT CONFIGURATION (SAFE VERSION)
# ============================================================================

# Function to show current configuration (hides passwords)
show_config() {
    echo "=== MediaWiki Configuration ==="
    echo "URL: $MEDIAWIKI_URL"
    echo "Username: $MEDIAWIKI_USERNAME"
    echo "Password: ********"
    echo "API Path: $MEDIAWIKI_API_PATH"
    echo "Timeout: ${MEDIAWIKI_TIMEOUT}s"
    echo "Debug: $DEBUG"
    echo "SSL Verify: $MEDIAWIKI_VERIFY_SSL"
    
    if [ -n "$MEDIAWIKI_PROXY" ]; then
        echo "Proxy: $MEDIAWIKI_PROXY"
    fi
    
    if [ -n "$MEDIAWIKI_COOKIE_FILE" ]; then
        echo "Cookie File: $MEDIAWIKI_COOKIE_FILE"
    fi
}

# ============================================================================
# INITIALIZATION
# ============================================================================

# Show configuration when sourced in debug mode
if [ "$DEBUG" = "true" ]; then
    show_config
fi

# Validate configuration if all required fields are set
if [ -n "$MEDIAWIKI_URL" ] && [ -n "$MEDIAWIKI_USERNAME" ] && [ -n "$MEDIAWIKI_PASSWORD" ]; then
    if [ "$DEBUG" = "true" ]; then
        validate_config
    fi
fi