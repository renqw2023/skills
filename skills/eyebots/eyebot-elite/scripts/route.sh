#!/bin/bash

# Eyebot Elite - Intelligent Agent Router
# Routes natural language requests to the appropriate Eyebot agent
#
# Usage: ./route.sh "your natural language request"
# Example: ./route.sh "swap 1 ETH for USDC on Base"
#
# Treasury: 0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9

set -e

API_BASE="${EYEBOT_API:-http://93.186.255.184:8001}"
TREASURY="0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# The 15 Elite Agents and their triggers
declare -A AGENT_TRIGGERS
AGENT_TRIGGERS[tokenforge]="deploy|create token|erc20|erc721|nft|mint|tokenomics|contract"
AGENT_TRIGGERS[liquidbot]="liquidity|lp|pool|amm|pair|add liquidity|remove liquidity"
AGENT_TRIGGERS[tradebot]="swap|trade|exchange|buy|sell|convert|dex|trading"
AGENT_TRIGGERS[auditbot]="audit|security|vulnerability|scan|analyze|exploit|reentrancy"
AGENT_TRIGGERS[launchbot]="launch|presale|fair launch|ido|ico|fundraise|crowdsale"
AGENT_TRIGGERS[alphabot]="alpha|signals|trending|whale|smart money|intel|sentiment"
AGENT_TRIGGERS[socialbot]="tweet|post|announce|social|twitter|telegram|discord|shill"
AGENT_TRIGGERS[vaultbot]="vault|safe|multisig|custody|gnosis|secure wallet|treasury"
AGENT_TRIGGERS[bridgebot]="bridge|cross-chain|l2|layer 2|transfer to|arbitrum|optimism|base"
AGENT_TRIGGERS[yieldbot]="yield|farm|stake|apy|rewards|staking|harvest|compound"
AGENT_TRIGGERS[cronbot]="schedule|cron|automate|recurring|timer|periodic|daily|weekly"
AGENT_TRIGGERS[guardbot]="monitor|guard|alert|watch|rug|honeypot|scam|protect"
AGENT_TRIGGERS[predictionbot]="predict|bet|forecast|odds|polymarket|prediction|probability"
AGENT_TRIGGERS[walletbot]="wallet|balance|send|receive|address|transaction|nonce|gas"
AGENT_TRIGGERS[lightningbot]="lightning|bitcoin|sats|satoshis|invoice|ln|btc|bolt11"

# Agent descriptions
declare -A AGENT_DESC
AGENT_DESC[tokenforge]="Token deployment and smart contracts"
AGENT_DESC[liquidbot]="Liquidity pool management"
AGENT_DESC[tradebot]="Trading and swaps"
AGENT_DESC[auditbot]="Security audits"
AGENT_DESC[launchbot]="Token launches and presales"
AGENT_DESC[alphabot]="Market intelligence"
AGENT_DESC[socialbot]="Social media automation"
AGENT_DESC[vaultbot]="Secure wallet management"
AGENT_DESC[bridgebot]="Cross-chain bridging"
AGENT_DESC[yieldbot]="Yield farming"
AGENT_DESC[cronbot]="Task scheduling"
AGENT_DESC[guardbot]="Security monitoring"
AGENT_DESC[predictionbot]="Prediction markets"
AGENT_DESC[walletbot]="EVM wallet operations"
AGENT_DESC[lightningbot]="Lightning Network"

# Function to detect the best agent for a request
detect_agent() {
    local request="$1"
    local request_lower=$(echo "$request" | tr '[:upper:]' '[:lower:]')
    local best_agent=""
    local best_score=0
    
    for agent in "${!AGENT_TRIGGERS[@]}"; do
        local triggers="${AGENT_TRIGGERS[$agent]}"
        local score=0
        
        # Split triggers by | and check each
        IFS='|' read -ra TRIGGER_ARRAY <<< "$triggers"
        for trigger in "${TRIGGER_ARRAY[@]}"; do
            if [[ "$request_lower" == *"$trigger"* ]]; then
                ((score++))
            fi
        done
        
        if [ $score -gt $best_score ]; then
            best_score=$score
            best_agent=$agent
        fi
    done
    
    if [ -z "$best_agent" ]; then
        # Default to walletbot for generic requests
        best_agent="walletbot"
    fi
    
    echo "$best_agent"
}

# Function to call an agent
call_agent() {
    local agent="$1"
    local request="$2"
    local chain="${3:-ethereum}"
    
    echo -e "${BLUE}Calling $agent...${NC}"
    
    local response=$(curl -s -X POST "${API_BASE}/api/${agent}" \
        -H "Content-Type: application/json" \
        -d "{
            \"request\": \"$request\",
            \"chain\": \"$chain\",
            \"auto_pay\": true,
            \"treasury\": \"$TREASURY\"
        }" 2>&1)
    
    echo "$response"
}

# Function to check API health
check_health() {
    local health=$(curl -s "${API_BASE}/api/health" 2>&1)
    if [[ "$health" == *"ok"* ]] || [[ "$health" == *"healthy"* ]]; then
        return 0
    else
        return 1
    fi
}

# Main function
main() {
    if [ $# -eq 0 ]; then
        echo -e "${YELLOW}Eyebot Elite Router${NC}"
        echo ""
        echo "Usage: $0 \"your request in natural language\""
        echo ""
        echo "Examples:"
        echo "  $0 \"deploy a token called PEPE with 1 billion supply\""
        echo "  $0 \"swap 1 ETH for USDC on Base\""
        echo "  $0 \"audit contract 0x1234...\""
        echo "  $0 \"bridge 1000 USDC to Arbitrum\""
        echo ""
        echo -e "${BLUE}Available Agents:${NC}"
        for agent in "${!AGENT_DESC[@]}"; do
            echo "  • $agent - ${AGENT_DESC[$agent]}"
        done
        echo ""
        echo -e "Treasury: ${GREEN}$TREASURY${NC}"
        exit 1
    fi
    
    local request="$*"
    
    echo -e "${YELLOW}╔════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║          EYEBOT ELITE ROUTER              ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check API health
    echo -e "${BLUE}Checking API status...${NC}"
    if ! check_health; then
        echo -e "${RED}Warning: API may be unavailable. Proceeding anyway...${NC}"
    else
        echo -e "${GREEN}API is healthy ✓${NC}"
    fi
    echo ""
    
    # Detect the best agent
    echo -e "${BLUE}Analyzing request:${NC} \"$request\""
    local agent=$(detect_agent "$request")
    echo -e "${GREEN}Routing to:${NC} $agent (${AGENT_DESC[$agent]})"
    echo ""
    
    # Call the agent
    echo -e "${YELLOW}─────────────────────────────────────────────${NC}"
    local result=$(call_agent "$agent" "$request")
    echo -e "${YELLOW}─────────────────────────────────────────────${NC}"
    echo ""
    
    # Display result
    if command -v jq &> /dev/null; then
        echo -e "${GREEN}Response:${NC}"
        echo "$result" | jq . 2>/dev/null || echo "$result"
    else
        echo -e "${GREEN}Response:${NC}"
        echo "$result"
    fi
    
    echo ""
    echo -e "${BLUE}Payment sent to treasury:${NC} $TREASURY"
}

# Handle specific commands
case "${1:-}" in
    --list|list)
        echo "Available Eyebot Agents:"
        for agent in "${!AGENT_DESC[@]}"; do
            echo "  $agent - ${AGENT_DESC[$agent]}"
        done
        ;;
    --health|health)
        if check_health; then
            echo -e "${GREEN}Eyebot API is healthy${NC}"
            exit 0
        else
            echo -e "${RED}Eyebot API is unavailable${NC}"
            exit 1
        fi
        ;;
    --detect|detect)
        shift
        agent=$(detect_agent "$*")
        echo "$agent"
        ;;
    --help|help|-h)
        echo "Eyebot Elite Router"
        echo ""
        echo "Commands:"
        echo "  route.sh \"request\"     Route a natural language request"
        echo "  route.sh --list        List all available agents"
        echo "  route.sh --health      Check API health"
        echo "  route.sh --detect      Detect agent without calling"
        echo ""
        echo "Environment Variables:"
        echo "  EYEBOT_API             Override API base URL"
        echo ""
        echo "Treasury: $TREASURY"
        ;;
    *)
        main "$@"
        ;;
esac
