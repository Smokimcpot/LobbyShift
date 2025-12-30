#!/bin/bash

# LobbyShift Installer
# Supports: Ubuntu 20.04+, Debian 11+, Raspberry Pi OS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
INSTALL_DIR="/opt/lobbyshift"
CONFIG_DIR="/etc/lobbyshift"
CONFIGS_DIR="$CONFIG_DIR/configs"
SERVICE_USER="lobbyshift"
WEB_PORT=8080

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════╗"
    echo "║         LobbyShift Installer          ║"
    echo "║   Self-hosted CoD Lobby Optimizer     ║"
    echo "╚═══════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect OS"
        exit 1
    fi
    
    log_info "Detected OS: $OS $VERSION"
}

detect_interface() {
    # Find the main network interface (not loopback, not docker)
    INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
    
    if [ -z "$INTERFACE" ]; then
        log_error "Could not detect network interface"
        exit 1
    fi
    
    log_info "Detected network interface: $INTERFACE"
}

install_dependencies() {
    log_info "Installing dependencies..."
    
    apt-get update
    apt-get install -y \
        wireguard \
        wireguard-tools \
        python3 \
        python3-pip \
        python3-venv \
        iptables \
        iptables-persistent \
        curl \
        git
    
    log_info "Dependencies installed"
}

create_user() {
    if id "$SERVICE_USER" &>/dev/null; then
        log_info "User $SERVICE_USER already exists"
    else
        log_info "Creating service user..."
        useradd -r -s /bin/false $SERVICE_USER
    fi
}

setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p $INSTALL_DIR
    mkdir -p $CONFIG_DIR
    mkdir -p $CONFIGS_DIR
    mkdir -p /var/log/lobbyshift
    
    # Copy application files
    if [ -d "$(dirname "$0")/lobbyshift" ]; then
        cp -r "$(dirname "$0")"/* $INSTALL_DIR/
    fi
    
    # Set permissions
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chown -R $SERVICE_USER:$SERVICE_USER $CONFIG_DIR
    chown -R $SERVICE_USER:$SERVICE_USER /var/log/lobbyshift
    
    # WireGuard configs need root access
    chmod 700 $CONFIGS_DIR
}

setup_python() {
    log_info "Setting up Python environment..."
    
    cd $INSTALL_DIR
    python3 -m venv venv
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    deactivate
}

create_config() {
    log_info "Creating configuration..."
    
    cat > $CONFIG_DIR/config.yaml << EOF
# LobbyShift Configuration

# Network interface (auto-detected)
interface: $INTERFACE

# Server IP
server_ip: $(hostname -I | awk '{print $1}')

# CoD matchmaking IP ranges
allowed_ips:
  - 185.34.0.0/16

# Web interface settings
web_port: $WEB_PORT
web_host: 0.0.0.0

# Auto-start VPN on boot
autostart: false
autostart_config: ""

# Logging
log_level: INFO
log_file: /var/log/lobbyshift/lobbyshift.log
EOF
    
    chmod 600 $CONFIG_DIR/config.yaml
}

setup_networking() {
    log_info "Configuring networking..."
    
    # Enable IP forwarding
    echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-lobbyshift.conf
    sysctl -w net.ipv4.ip_forward=1
    
    # Get local subnet
    LOCAL_SUBNET=$(ip -o -f inet addr show $INTERFACE | awk '{print $4}' | head -n1)
    
    # Convert to network address (e.g., 192.168.1.108/24 -> 192.168.1.0/24)
    if [ -n "$LOCAL_SUBNET" ]; then
        LOCAL_SUBNET=$(echo $LOCAL_SUBNET | sed 's/\.[0-9]*\//.0\//')
    else
        LOCAL_SUBNET="192.168.1.0/24"
        log_warn "Could not detect subnet, using default: $LOCAL_SUBNET"
    fi
    
    log_info "Local subnet: $LOCAL_SUBNET"
    
    # Create iptables rules script
    cat > $CONFIG_DIR/iptables-rules.sh << 'EOFSCRIPT'
#!/bin/bash
# LobbyShift iptables rules

INTERFACE="PLACEHOLDER_INTERFACE"
LOCAL_SUBNET="PLACEHOLDER_SUBNET"
COD_IPS="185.34.0.0/16"

# Flush existing LobbyShift rules (marked with comment)
iptables -t nat -S 2>/dev/null | grep "lobbyshift" | while read rule; do
    iptables -t nat $(echo $rule | sed 's/-A/-D/') 2>/dev/null
done

iptables -S 2>/dev/null | grep "lobbyshift" | while read rule; do
    iptables $(echo $rule | sed 's/-A/-D/') 2>/dev/null
done

# ============================================
# GATEWAY MODE - Forward all traffic from LAN
# ============================================

# NAT for all outgoing traffic from LAN (this allows PS5/Xbox to access internet)
iptables -t nat -A POSTROUTING -o $INTERFACE -s $LOCAL_SUBNET -j MASQUERADE -m comment --comment "lobbyshift-gateway"

# Allow forwarding from LAN to internet
iptables -A FORWARD -i $INTERFACE -s $LOCAL_SUBNET -j ACCEPT -m comment --comment "lobbyshift-gateway"

# Allow return traffic
iptables -A FORWARD -o $INTERFACE -d $LOCAL_SUBNET -m state --state RELATED,ESTABLISHED -j ACCEPT -m comment --comment "lobbyshift-gateway"

# ============================================
# VPN MODE - Route CoD traffic through VPN
# ============================================

# Only apply if VPN interface exists
if ip link show lobbyshift &>/dev/null; then
    # NAT for VPN traffic
    iptables -t nat -A POSTROUTING -o lobbyshift -j MASQUERADE -m comment --comment "lobbyshift-vpn"
    
    # Forward CoD traffic to VPN
    iptables -A FORWARD -i $INTERFACE -o lobbyshift -s $LOCAL_SUBNET -d $COD_IPS -j ACCEPT -m comment --comment "lobbyshift-vpn"
    
    # Allow return traffic from VPN
    iptables -A FORWARD -i lobbyshift -o $INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT -m comment --comment "lobbyshift-vpn"
fi

echo "iptables rules applied successfully"
EOFSCRIPT

    # Replace placeholders with actual values
    sed -i "s/PLACEHOLDER_INTERFACE/$INTERFACE/g" $CONFIG_DIR/iptables-rules.sh
    sed -i "s|PLACEHOLDER_SUBNET|$LOCAL_SUBNET|g" $CONFIG_DIR/iptables-rules.sh
    
    chmod +x $CONFIG_DIR/iptables-rules.sh
    
    # Apply rules
    log_info "Applying iptables rules..."
    bash $CONFIG_DIR/iptables-rules.sh
    
    # Save iptables rules
    log_info "Saving iptables rules..."
    netfilter-persistent save
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/lobbyshift.service << EOF
[Unit]
Description=LobbyShift - CoD Lobby Optimizer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStartPre=$CONFIG_DIR/iptables-rules.sh
ExecStart=$INSTALL_DIR/venv/bin/python -m lobbyshift.main
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lobbyshift

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable lobbyshift
}

create_cli() {
    log_info "Creating CLI command..."
    
    cat > /usr/local/bin/lobbyshift << 'EOF'
#!/bin/bash

API_URL="http://localhost:8080/api"

case "$1" in
    status)
        curl -s "$API_URL/status" | python3 -m json.tool
        ;;
    list)
        curl -s "$API_URL/configs" | python3 -m json.tool
        ;;
    switch)
        if [ -z "$2" ]; then
            echo "Usage: lobbyshift switch <config_name>"
            exit 1
        fi
        curl -s -X POST "$API_URL/switch/$2" | python3 -m json.tool
        ;;
    up)
        curl -s -X POST "$API_URL/up" | python3 -m json.tool
        ;;
    down)
        curl -s -X POST "$API_URL/down" | python3 -m json.tool
        ;;
    restart)
        sudo systemctl restart lobbyshift
        echo "LobbyShift restarted"
        ;;
    logs)
        sudo journalctl -u lobbyshift -f
        ;;
    iptables)
        echo "=== NAT Rules ==="
        sudo iptables -t nat -L -v -n | grep -E "lobbyshift|Chain"
        echo ""
        echo "=== Forward Rules ==="
        sudo iptables -L FORWARD -v -n | grep -E "lobbyshift|Chain"
        ;;
    *)
        echo "LobbyShift CLI"
        echo ""
        echo "Usage: lobbyshift <command>"
        echo ""
        echo "Commands:"
        echo "  status    Show current VPN status"
        echo "  list      List available configs"
        echo "  switch    Switch to a config (e.g., lobbyshift switch mexico)"
        echo "  up        Start VPN"
        echo "  down      Stop VPN"
        echo "  restart   Restart LobbyShift service"
        echo "  logs      Show live logs"
        echo "  iptables  Show current iptables rules"
        ;;
esac
EOF
    
    chmod +x /usr/local/bin/lobbyshift
}

print_success() {
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Installation Complete! 🎉         ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Web Interface: ${BLUE}http://$SERVER_IP:$WEB_PORT${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open the web interface"
    echo "  2. Upload your WireGuard VPN config"
    echo "  3. Set your console/PC gateway to: $SERVER_IP"
    echo ""
    echo "Console Network Settings:"
    echo "  Gateway: $SERVER_IP"
    echo "  DNS: Your router IP or 8.8.8.8"
    echo ""
    echo "CLI commands:"
    echo "  lobbyshift status   - Show status"
    echo "  lobbyshift list     - List configs"
    echo "  lobbyshift switch   - Switch region"
    echo "  lobbyshift iptables - Show firewall rules"
    echo ""
    echo "Start the service:"
    echo "  sudo systemctl start lobbyshift"
    echo ""
}

# Main
main() {
    print_banner
    check_root
    detect_os
    detect_interface
    install_dependencies
    create_user
    setup_directories
    setup_python
    create_config
    setup_networking
    create_systemd_service
    create_cli
    print_success
}

main "$@"
