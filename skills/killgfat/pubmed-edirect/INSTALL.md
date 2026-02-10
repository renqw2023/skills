# EDirect Installation and Configuration

## Prerequisites

- Unix-like system (Linux, macOS, or Windows with Cygwin/WSL)
- Internet connection
- curl or wget installed

**Important:** This skill uses **local installation only** – no Docker or containers required. All tools run directly on your system.

**Security Advisory:** Always verify the source of any installation script. The official NCBI EDirect installer is hosted at `ftp.ncbi.nlm.nih.gov`. When using automated installation, download the script to a file first and review it if desired, rather than piping directly to your shell. This protects against potential supply-chain attacks or compromised mirrors.

## Installation Methods

### Method 1: Secure Automated Installation

We recommend downloading the installer script first for review before execution:

```bash
# Download the installer script
curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh -o install-edirect.sh

# Optional: Review the script for transparency
less install-edirect.sh  # or open in your editor

# Make it executable
chmod +x install-edirect.sh

# Run the installer
./install-edirect.sh
```

Alternatively, using wget:

```bash
wget -q https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh -O install-edirect.sh
chmod +x install-edirect.sh
./install-edirect.sh
```

This script will:
1. Download EDirect scripts and programs from the official NCBI repository
2. Create an `edirect` folder in your home directory
3. Add the directory to your PATH

**Security Note:** Avoid piping remote scripts directly to your shell (e.g., `sh -c "curl | bash"`). Downloading first allows you to verify the content before execution, following best security practices.

### Method 2: Manual Installation (Alternative)

If the automated script doesn't work, you can manually install:

```bash
# Create edirect directory
mkdir -p ~/edirect
cd ~/edirect

# Download and extract the package
curl -O https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/edirect.tar.gz
tar -xzf edirect.tar.gz

# Add to PATH
echo 'export PATH="$HOME/edirect:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Post-Installation Configuration

### 1. Configure API Key (Highly Recommended)

For increased rate limits (10 requests/second vs 3 requests/second), obtain an API key:

1. Create an NCBI account at https://www.ncbi.nlm.nih.gov/
2. Go to Account Settings → API Key Management
3. Generate a new API key

Add the API key to your environment:

```bash
# For current session
export NCBI_API_KEY=your_api_key_here

# For permanent configuration
echo 'export NCBI_API_KEY="your_api_key_here"' >> ~/.bashrc
echo 'export NCBI_API_KEY="your_api_key_here"' >> ~/.zshrc  # If using zsh
```

### 2. Configure Email Address (Optional but Recommended)

NCBI requests that you identify yourself with an email address:

```bash
export NCBI_EMAIL="your.email@example.com"
echo 'export NCBI_EMAIL="your.email@example.com"' >> ~/.bashrc
```

### 3. Set Tool Configuration

EDirect tools can be configured with default options:

```bash
# Create configuration file if needed
touch ~/.ncbirc

# Set default format preferences
export EFETCH_FORMAT="xml"  # Default output format
```

## Verification

Test your installation:

```bash
# Check if commands are available
esearch -help
efetch -help

# Test a simple query
esearch -db pubmed -query "test" -retmax 1
```

Expected output should show help text without errors.

## Troubleshooting

### Common Issues

#### 1. "Command not found"
```bash
# Check if edirect is in PATH
echo $PATH | grep edirect

# If not, add it manually
export PATH="$HOME/edirect:$PATH"
```

#### 2. Permission Denied
```bash
# Make scripts executable
chmod +x ~/edirect/*.pl
chmod +x ~/edirect/*.pm
```

#### 3. Perl Module Errors
EDirect requires certain Perl modules. Install them:

```bash
# On Ubuntu/Debian
sudo apt-get install perl libwww-perl libxml-simple-perl

# On CentOS/RHEL
sudo yum install perl perl-libwww-perl perl-XML-Simple

# On macOS with Homebrew
brew install perl
cpan install LWP::Simple XML::Simple
```

#### 4. Proxy Configuration
If behind a proxy:

```bash
export ftp_proxy="http://proxy.example.com:8080"
export http_proxy="http://proxy.example.com:8080"
export https_proxy="http://proxy.example.com:8080"
```

#### 5. SSL Certificate Issues
If you encounter SSL certificate errors, update your system's CA certificates:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ca-certificates

# CentOS/RHEL
sudo yum update ca-certificates

# macOS
brew install ca-certificates
```

Also ensure your system time is correct:
```bash
date  # check system time
# If incorrect, sync with NTP
sudo ntpdate pool.ntp.org  # or use timedatectl
```

**Important:** Never disable SSL verification by setting PERL_LWP_SSL_VERIFY_HOSTNAME=0 in production or when handling sensitive data. This weakens security and exposes you to man-in-the-middle attacks.

## Performance Tuning

### 1. Increase Timeouts for Large Queries
```bash
export EUTILS_TIMEOUT=60  # Increase timeout to 60 seconds
```

### 2. Enable Compression for Large Transfers
```bash
export EUTILS_COMPRESS=1  # Enable gzip compression
```

### 3. Cache Configuration
```bash
# Set cache directory
export NCBI_CACHE_DIR="$HOME/.ncbi/cache"
mkdir -p "$NCBI_CACHE_DIR"
```

## Uninstallation

To remove EDirect:

```bash
# Remove the edirect directory
rm -rf ~/edirect

# Remove from PATH in your shell configuration files
# Edit ~/.bashrc, ~/.bash_profile, ~/.zshrc, etc.
# Remove the line: export PATH="$HOME/edirect:$PATH"
```

## Platform-Specific Notes

### macOS
- Comes with Perl pre-installed
- May need to install command line tools: `xcode-select --install`

### Windows (WSL/Cygwin)
- Works well with Windows Subsystem for Linux (WSL)
- Cygwin requires Perl and related packages

### Linux Servers
- Most distributions have required Perl modules in repositories
- Consider using `screen` or `tmux` for long-running queries

## Next Steps

After installation, proceed to:
- [BASICS.md](BASICS.md) for basic usage
- [EXAMPLES.md](EXAMPLES.md) for practical examples
- [ADVANCED.md](ADVANCED.md) for advanced techniques