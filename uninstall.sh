#!/bin/bash

# LobbyShift Uninstaller
# Completely removes LobbyShift installation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${RED}"
    echo "╔═══════════════════════════════════════╗"
    echo "║        LobbyShift Uninstaller         ║"
    echo "╚═══════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[ERROR]${NC} This script must be run as root (use sudo)"
        exit 1
    fi
}

confirm_uninstall() {
    echo ""
    echo -e "${YELLOW}This will completely remove LobbyShift including:${NC}"
    echo "  - Service and systemd files"
    echo "  - All configurations"
    echo "  - All VPN configs"
    echo "  - iptables rules"
    echo "  - Log files"
    echo "  - User account"
    echo ""
    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Uninstall cancelled."
        exit 0
    fi
}

stop_services() {
    log_info "Stopping services..."
    
    # Stop systemd service
    systemctl stop lobbyshift 2>/dev/null || true
    systemctl disable lobbyshift 2>/dev/null || true
    
    # Stop WireGuard interface
    wg-quick down lobbyshift 2>/dev/null || true
    ip link delete lobbyshift 2>/dev/null || true
}

remove_systemd() {
    log_info "Removing systemd service..."
    
    rm -f /etc/systemd/system/lobbyshift.service
    systemctl daemon-reload
}

remove_iptables() {
    log_info "Removing iptables rules..."
    
    # Remove NAT rules
    iptables -t nat -S 2>/dev/null | grep "lobbyshift" | while read rule; do
        iptables -t nat $(echo $rule | sed 's/-A/-D/') 2>/dev/null || true
    done
    
    # Remove FORWARD rules
    iptables -S 2>/dev/null | grep "lobbyshift" | while read rule; do
        iptables $(echo $rule | sed 's/-A/-D/') 2>/dev/null || true
    done
    
    # Save iptables
    netfilter-persistent save 2>/dev/null || true
}

remove_files() {
    log_info "Removing installation files..."
    
    # Main installation
    rm -rf /opt/lobbyshift
    
    # Configuration
    rm -rf /etc/lobbyshift
    
    # Logs
    rm -rf /var/log/lobbyshift
    
    # WireGuard configs
    rm -f /etc/wireguard/wg-lobbyshift*.conf
    rm -f /etc/wireguard/lobbyshift.conf
    
    # CLI
    rm -f /usr/local/bin/lobbyshift
}

remove_user() {
    log_info "Removing service user..."
    
    userdel lobbyshift 2>/dev/null || true
}

verify_removal() {
    echo ""
    echo -e "${BLUE}Verification:${NC}"
    
    # Check each component
    if [ -d "/opt/lobbyshift" ]; then
        log_warn "/opt/lobbyshift still exists"
    else
        log_info "/opt/lobbyshift removed"
    fi
    
    if [ -d "/etc/lobbyshift" ]; then
        log_warn "/etc/lobbyshift still exists"
    else
        log_info "/etc/lobbyshift removed"
    fi
    
    if id "lobbyshift" &>/dev/null; then
        log_warn "User lobbyshift still exists"
    else
        log_info "User lobbyshift removed"
    fi
    
    if iptables -t nat -L -n 2>/dev/null | grep -q "lobbyshift"; then
        log_warn "Some iptables rules still exist"
    else
        log_info "iptables rules removed"
    fi
    
    if systemctl is-enabled lobbyshift &>/dev/null; then
        log_warn "Service still enabled"
    else
        log_info "Service disabled"
    fi
}

print_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Uninstall Complete! 🧹            ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo "LobbyShift has been completely removed."
    echo ""
    echo "To reinstall:"
    echo "  cd ~/LobbyShift"
    echo "  sudo ./install.sh"
    echo ""
}

# Main
main() {
    print_banner
    check_root
    confirm_uninstall
    stop_services
    remove_systemd
    remove_iptables
    remove_files
    remove_user
    verify_removal
    print_success
}

main "$@"
