# 🎮 LobbyShift

<p align="center">
  <strong>Self-hosted VPN Gateway for CoD Matchmaking Optimization</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi%20%7C%20Ubuntu%20%7C%20Debian-blue" alt="Platform">
  <img src="https://img.shields.io/badge/License-CC%20BY--NC%204.0-green" alt="License">
  <img src="https://img.shields.io/badge/Python-3.9%2B-yellow" alt="Python">
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-faq">FAQ</a>
</p>

---

## 🎯 What is LobbyShift?

LobbyShift is a **free, self-hosted alternative** to paid services like NoLagVPN or LobbyGod. It turns your Raspberry Pi or Ubuntu server into a smart VPN gateway that routes only Call of Duty matchmaking traffic through VPN servers in different regions – giving you access to easier lobbies while keeping your ping low.

**No subscriptions. No monthly fees. Full control.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌍 **Region Switching** | Switch between VPN configs for different countries with one click |
| 🎯 **Split Tunneling** | Only CoD matchmaking traffic (185.34.0.0/16) goes through VPN |
| ⚡ **Low Latency** | Game traffic stays direct – only matchmaking is routed |
| 🖥️ **Web Interface** | Beautiful dark/light mode UI accessible from any device |
| ⭐ **Favorites** | Pin your best-performing regions to the top |
| 📜 **Connection History** | Track which regions you've used and when |
| 🌐 **Auto Country Detection** | Automatically detects VPN server location via GeoIP |
| 📱 **Console Support** | Works with PS5, Xbox, and PC |
| 🔒 **Privacy** | Self-hosted, no data leaves your network |

---

## 🔧 How It Works

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│   PS5 /     │      │   LobbyShift     │      │   Router    │
│   Xbox /    │─────▶│   Gateway        │─────▶│             │──▶ Internet
│   PC        │      │   (Raspberry Pi) │      │             │
└─────────────┘      └────────┬─────────┘      └─────────────┘
                              │
                              │ Only 185.34.0.0/16
                              ▼
                     ┌──────────────────┐
                     │   WireGuard VPN  │
                     │   (Mexico/TR/etc)│
                     └──────────────────┘
```

1. Your console/PC uses LobbyShift as its network gateway
2. Regular traffic (YouTube, downloads, etc.) goes directly to the internet
3. Only CoD matchmaking IPs are routed through the VPN
4. Matchmaking sees you in Mexico/Turkey/etc. → easier lobbies
5. Actual gameplay connects directly → low ping

---

## 📋 Requirements

- **Hardware:** Raspberry Pi 4+ or any Ubuntu/Debian server
- **OS:** Ubuntu 20.04+, Debian 11+, or Raspberry Pi OS
- **VPN:** WireGuard-compatible VPN with servers in desired regions:
  - [ProtonVPN](https://protonvpn.com) – **Free tier works!** (limited countries) or Plus for more regions
  - [Mullvad](https://mullvad.net)
  - [IVPN](https://ivpn.net)
  - [Windscribe](https://windscribe.com)
  - Any custom WireGuard server

> **💡 Tip:** ProtonVPN Free includes servers in Japan, Netherlands, and USA. These can already make a difference for matchmaking. Upgrade to Plus for access to Mexico, Turkey, Egypt, and other "bot lobby" regions.

### Recommended VPN Regions for Bot Lobbies

| Region | Country Code | Difficulty | ProtonVPN |
|--------|--------------|------------|-----------|
| 🇲🇽 Mexico | MX | ⭐ Easy | Plus |
| 🇹🇷 Turkey | TR | ⭐ Easy | Plus |
| 🇪🇬 Egypt | EG | ⭐ Easy | Plus |
| 🇿🇦 South Africa | ZA | ⭐ Easy | Plus |
| 🇯🇵 Japan | JP | ⭐⭐ Medium | **Free** ✓ |
| 🇳🇱 Netherlands | NL | ⭐⭐ Medium | **Free** ✓ |
| 🇺🇸 USA | US | ⭐⭐⭐ Hard | **Free** ✓ |
| 🇧🇷 Brazil | BR | ⭐⭐ Medium | Plus |
| 🇦🇷 Argentina | AR | ⭐ Easy | Plus |

---

## 🚀 Installation

### Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/Smokimcpot/LobbyShift.git
cd LobbyShift

# Run the installer
chmod +x install.sh
sudo ./install.sh
```

The installer will:
- ✅ Install WireGuard and dependencies
- ✅ Set up the Python environment
- ✅ Configure networking and iptables
- ✅ Create systemd service for auto-start
- ✅ Set up the web interface

### Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

```bash
# Install dependencies
sudo apt update
sudo apt install -y wireguard wireguard-tools python3 python3-pip python3-venv iptables iptables-persistent

# Create directories
sudo mkdir -p /opt/lobbyshift
sudo mkdir -p /etc/lobbyshift/configs

# Clone and copy files
git clone https://github.com/Smokimcpot/LobbyShift.git
cd LobbyShift
sudo cp -r * /opt/lobbyshift/

# Set up Python environment
cd /opt/lobbyshift
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt

# Enable IP forwarding
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-lobbyshift.conf
sudo sysctl -w net.ipv4.ip_forward=1

# Install and enable service
sudo cp systemd/lobbyshift.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lobbyshift
sudo systemctl start lobbyshift
```

</details>

---

## 📖 Usage

### 1. Access the Web Interface

Open your browser and go to:
```
http://<YOUR-SERVER-IP>:8080
```

### 2. Upload VPN Configs

1. Download WireGuard configs from your VPN provider
2. Open LobbyShift web interface
3. Drag & drop or click to upload `.conf` files
4. LobbyShift automatically configures split tunneling

### 3. Configure Your Console/PC

#### PlayStation 5

1. Go to **Settings → Network → Settings → Set Up Internet Connection**
2. Select your connection → **Advanced Settings**
3. Configure as follows:

| Setting | Value |
|---------|-------|
| IP Address | Automatic (or keep your current) |
| Subnet Mask | `255.255.255.0` |
| **Gateway** | **Your LobbyShift server IP** (e.g., `192.168.1.100`) |
| DNS Primary | Your router IP (e.g., `192.168.1.1`) |
| DNS Secondary | `8.8.8.8` or `1.1.1.1` |

4. Save and test connection

#### Xbox Series X|S

1. Go to **Settings → General → Network Settings → Advanced Settings**
2. Select **IP Settings → Manual**
3. Configure as follows:

| Setting | Value |
|---------|-------|
| IP Address | Keep your current |
| Subnet Mask | `255.255.255.0` |
| **Gateway** | **Your LobbyShift server IP** (e.g., `192.168.1.100`) |
| DNS Primary | Your router IP or `8.8.8.8` |
| DNS Secondary | `1.1.1.1` |

4. Save settings

#### PC

1. Go to **Network Settings → Change Adapter Options**
2. Right-click your connection → **Properties → IPv4**
3. Set **Default Gateway** to your LobbyShift server IP

### 4. Switch Regions

1. Open the web interface
2. Click **Switch** on any config
3. **Restart your game** for changes to take effect
4. Enjoy easier lobbies! 🎮

---

## 🖥️ Web Interface Features

- **VPN Status** – See connection status, endpoint, and transfer stats
- **Region Switching** – One-click switching between configs
- **Favorites** – Star your best regions for quick access
- **Connection History** – Track your usage over time
- **Dark/Light Mode** – Easy on the eyes
- **Mobile Friendly** – Works on phone and tablet

---

## ⌨️ CLI Commands

```bash
# Check status
lobbyshift status

# List available configs
lobbyshift list

# Switch to a config
lobbyshift switch mexico

# Start/Stop VPN
lobbyshift up
lobbyshift down

# View live logs
lobbyshift logs

# Restart service
lobbyshift restart
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Current VPN status |
| `/api/configs` | GET | List all configs |
| `/api/configs` | POST | Upload new config |
| `/api/configs/{name}` | GET | Get config content |
| `/api/configs/{name}` | PUT | Update config |
| `/api/configs/{name}` | DELETE | Delete config |
| `/api/switch/{name}` | POST | Switch to config |
| `/api/up` | POST | Start VPN |
| `/api/down` | POST | Stop VPN |
| `/api/favorites` | GET | List favorites |
| `/api/favorites/{name}` | POST | Add favorite |
| `/api/favorites/{name}` | DELETE | Remove favorite |
| `/api/logs` | GET | Connection history |
| `/api/logs` | DELETE | Clear history |

---

## ❓ FAQ

<details>
<summary><strong>Does this work with Warzone 2/MW3/Black Ops 6?</strong></summary>

Yes! LobbyShift works with all Call of Duty titles that use the 185.34.0.0/16 IP range for matchmaking.

</details>

<details>
<summary><strong>Will I get banned?</strong></summary>

Using a VPN technically violates Activision's Terms of Service. However, thousands of players use VPN services daily without issues. The risk is low, but use at your own discretion. Using an alt account is recommended.

</details>

<details>
<summary><strong>Why is my ping still high?</strong></summary>

Make sure your config only routes matchmaking IPs. Check that `AllowedIPs` in your WireGuard config is set to `185.34.0.0/16` and NOT `0.0.0.0/0`. LobbyShift does this automatically when you upload configs.

</details>

<details>
<summary><strong>Can I use this on multiple devices?</strong></summary>

Yes! Any device that uses your LobbyShift server as its gateway will have its CoD traffic routed through the VPN.

</details>

<details>
<summary><strong>Do I need a paid VPN subscription?</strong></summary>

Not necessarily! **ProtonVPN Free** works and includes servers in Japan, Netherlands, and USA. For more "bot lobby" regions like Mexico, Turkey, or Egypt, you'll need ProtonVPN Plus or another paid VPN. But you can start testing with the free tier.

</details>

<details>
<summary><strong>Why not just use a regular VPN app?</strong></summary>

Regular VPN apps route ALL traffic through the VPN, causing high ping in games. LobbyShift only routes matchmaking traffic, so your actual gameplay stays on your fast local connection.

</details>

---

## 🛠️ Troubleshooting

### No internet after setting gateway

```bash
# Check if IP forwarding is enabled
cat /proc/sys/net/ipv4/ip_forward  # Should be 1

# Check iptables rules
sudo iptables -t nat -L -v -n
```

### VPN not connecting

```bash
# Check WireGuard status
sudo wg show

# Check service status
sudo systemctl status lobbyshift

# View logs
sudo journalctl -u lobbyshift -f
```

### Web interface not loading

```bash
# Check if service is running
sudo systemctl status lobbyshift

# Check port
sudo ss -tlnp | grep 8080
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas We Need Help

- 🐳 Docker support
- 📊 Lobby tracking integration
- 🌐 More VPN provider templates
- 📱 Mobile app
- 🌍 Translations

---

## ⚠️ Disclaimer

This tool is for **educational purposes only**. Using VPNs to manipulate matchmaking may violate game Terms of Service. The developers are not responsible for any bans or penalties. Use at your own risk.

---

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)**.

**You are free to:**
- ✅ Use for personal, non-commercial purposes
- ✅ Modify and adapt the code
- ✅ Share with others

**You may not:**
- ❌ Use for commercial purposes
- ❌ Sell or monetize this software
- ❌ Use in paid services or products

See [LICENSE](LICENSE) for details.

---

## ⭐ Support

If you find this project useful, please give it a star! ⭐

---

<p align="center">
  Made with ❤️ for the gaming community
</p>
