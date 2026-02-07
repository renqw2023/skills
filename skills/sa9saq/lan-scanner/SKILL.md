---
description: Discover devices and scan ports on your local network using nmap.
---

# network-scanner

Discover devices and scan ports on your local network using nmap.

**Use when** scanning network, finding devices on LAN, or checking open ports.

## Instructions

### Step 1: Determine Scan Target
Ask the user what to scan:
- **Full LAN discovery**: Detect the local subnet (e.g., `192.168.1.0/24`) from `ip route` or `ifconfig`.
- **Specific host**: IP address or hostname.
- **Port check**: Specific ports on a target.

### Step 2: Run the Scan
Use `nmap` with appropriate flags:
- **Host discovery**: `nmap -sn {subnet}` — find live hosts without port scanning.
- **Quick port scan**: `nmap -F {target}` — top 100 ports.
- **Full port scan**: `nmap -p- {target}` — all 65535 ports (slow).
- **Service detection**: `nmap -sV {target}` — identify services and versions.
- **OS detection**: `sudo nmap -O {target}` — requires root.

Parse the output into a clean table: IP, hostname, MAC, open ports, services.

### Step 3: Present Results
Format results as a readable table or list. Highlight:
- Total devices found
- Open ports and running services
- Any potential security concerns (e.g., open SSH, Telnet)

## Notes
- Requires `nmap` installed (`apt install nmap`).
- Some scans (OS detection, SYN scan) require root/sudo.
- Only scan networks you own or have permission to scan.
