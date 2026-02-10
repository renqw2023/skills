# MediaWiki Login Skill for OpenClaw

MediaWiki login and connection testing skill for OpenClaw. Provides simple commands to test connectivity, authenticate, and verify user permissions on MediaWiki instances.

## Features

- **Connection Testing**: Verify HTTP connectivity and API endpoint accessibility
- **Authentication**: Secure login with token-based authentication
- **User Information**: Retrieve detailed user info, groups, and permissions
- **Health Checks**: Comprehensive health check for MediaWiki instances
- **Debug Tools**: Detailed logging and API tracing for troubleshooting

## Installation

### From ClawHub (Recommended)
```bash
npx skills add mediawiki-login
```

### From GitHub
```bash
npx skills add https://github.com/delong2003/mediawiki-login.git
```

### Manual Installation
```bash
git clone https://github.com/delong2003/mediawiki-login.git
cd mediawiki-login
# Use the scripts directly
```

## Quick Start

1. **Copy configuration template**:
   ```bash
   cp config/mediawiki-config-template.sh config/mediawiki-config.sh
   ```

2. **Edit configuration**:
   ```bash
   nano config/mediawiki-config.sh
   ```
   Set your MediaWiki URL, username, and password.

3. **Test connection**:
   ```bash
   ./scripts/test_connection.sh
   ```

4. **Login and verify**:
   ```bash
   ./scripts/login.sh
   ./scripts/get_user_info.sh
   ```

5. **Run comprehensive health check**:
   ```bash
   ./scripts/health_check.sh
   ```

## Scripts Overview

### `test_connection.sh`
Tests basic connectivity to MediaWiki API without authentication.
```bash
./scripts/test_connection.sh [--debug] [--trace] [--config FILE]
```

### `login.sh`
Authenticates with MediaWiki and establishes a session.
```bash
./scripts/login.sh [--debug] [--cookie-file FILE] [--preserve-cookies]
```

### `get_user_info.sh`
Retrieves detailed user information after login.
```bash
./scripts/get_user_info.sh [--debug] [--cookie-file FILE]
```

### `health_check.sh`
Comprehensive health check for MediaWiki instances.
```bash
./scripts/health_check.sh [--debug]
```

## Configuration

### Required Configuration
Create `config/mediawiki-config.sh` with:
```bash
export MEDIAWIKI_URL="https://your-wiki.com"
export MEDIAWIKI_USERNAME="your_username"
export MEDIAWIKI_PASSWORD="your_password"
export MEDIAWIKI_API_PATH="/api.php"  # or /w/api.php
```

### Optional Configuration
```bash
export MEDIAWIKI_TIMEOUT="30"
export DEBUG="false"
export TRACE_API="false"
export MEDIAWIKI_COOKIE_FILE="/path/to/cookies.txt"
```

## Examples

### Basic Usage
```bash
# Load configuration
source config/mediawiki-config.sh

# Test connection
./scripts/test_connection.sh

# Login
./scripts/login.sh --preserve-cookies

# Use cookie file for subsequent requests
export MEDIAWIKI_COOKIE_FILE="/tmp/mediawiki-cookies.txt"
./scripts/get_user_info.sh
```

### Integration with Other Scripts
```bash
#!/bin/bash
# example-usage.sh

source config/mediawiki-config.sh

# Check if wiki is accessible
if ./scripts/test_connection.sh; then
    echo "Wiki is accessible"
    
    # Login and get user info
    if ./scripts/login.sh; then
        echo "Login successful"
        ./scripts/get_user_info.sh
    else
        echo "Login failed"
        exit 1
    fi
else
    echo "Cannot connect to wiki"
    exit 1
fi
```

## Security Best Practices

1. **Never commit** `config/mediawiki-config.sh` to version control
2. Add `config/mediawiki-config.sh` to `.gitignore`
3. Use environment variables for sensitive data
4. Clean up cookie files after use
5. Enable SSL verification for production use

## Troubleshooting

### Common Issues

#### Connection Failed
```bash
# Enable debug mode
DEBUG=true ./scripts/test_connection.sh

# Check URL and network connectivity
curl -I https://your-wiki.com
```

#### Login Failed
```bash
# Verify credentials
# Check if user account is active
# Ensure API path is correct (/w/api.php or /api.php)
```

#### Permission Errors
```bash
# Check user groups and rights
./scripts/get_user_info.sh
```

### Debug Mode
Enable debug output for detailed information:
```bash
export DEBUG=true
./scripts/login.sh
```

### API Tracing
Enable API tracing to see raw requests and responses:
```bash
export TRACE_API=true
export DEBUG=true
./scripts/test_connection.sh
```

## Skill Structure
```
mediawiki-login/
├── SKILL.md                    # Skill documentation
├── README.md                   # This file
├── package.json                # Package metadata
├── config/
│   ├── mediawiki-config-template.sh  # Configuration template
│   └── mediawiki-config.sh     # Actual configuration (.gitignore)
├── scripts/
│   ├── test_connection.sh      # Connection testing
│   ├── login.sh                # Authentication
│   ├── get_user_info.sh        # User information
│   └── health_check.sh         # Comprehensive health check
└── examples/
    └── example-usage.sh        # Usage examples
```

## Dependencies
- `bash` (shell)
- `curl` (HTTP client)
- `jq` (JSON processor)

## License
MIT License

## Support
- Issues: [GitHub Issues](https://github.com/delong2003/mediawiki-login/issues)
- Documentation: [OpenClaw Skills](https://docs.openclaw.ai/skills)

## Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-09  
**Maintainer**: OpenClaw Skills Team