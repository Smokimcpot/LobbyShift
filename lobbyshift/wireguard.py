"""
LobbyShift - WireGuard Management
"""

import os
import re
import asyncio
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import urllib.request
import socket


# Country code mapping for flags
COUNTRY_FLAGS = {
    "MX": "🇲🇽", "JP": "🇯🇵", "TR": "🇹🇷", "EG": "🇪🇬", "ZA": "🇿🇦",
    "KZ": "🇰🇿", "BR": "🇧🇷", "AR": "🇦🇷", "CL": "🇨🇱", "CO": "🇨🇴",
    "PE": "🇵🇪", "IN": "🇮🇳", "PH": "🇵🇭", "ID": "🇮🇩", "TH": "🇹🇭",
    "VN": "🇻🇳", "MY": "🇲🇾", "SG": "🇸🇬", "KR": "🇰🇷", "TW": "🇹🇼",
    "HK": "🇭🇰", "AE": "🇦🇪", "SA": "🇸🇦", "IL": "🇮🇱", "RU": "🇷🇺",
    "UA": "🇺🇦", "PL": "🇵🇱", "DE": "🇩🇪", "FR": "🇫🇷", "GB": "🇬🇧",
    "UK": "🇬🇧", "ES": "🇪🇸", "IT": "🇮🇹", "NL": "🇳🇱", "SE": "🇸🇪",
    "NO": "🇳🇴", "FI": "🇫🇮", "DK": "🇩🇰", "CH": "🇨🇭", "AT": "🇦🇹",
    "BE": "🇧🇪", "PT": "🇵🇹", "CZ": "🇨🇿", "RO": "🇷🇴", "HU": "🇭🇺",
    "GR": "🇬🇷", "US": "🇺🇸", "CA": "🇨🇦", "AU": "🇦🇺", "NZ": "🇳🇿",
    "IE": "🇮🇪", "IS": "🇮🇸", "LU": "🇱🇺", "SK": "🇸🇰", "SI": "🇸🇮",
    "HR": "🇭🇷", "BG": "🇧🇬", "RS": "🇷🇸", "LT": "🇱🇹", "LV": "🇱🇻",
    "EE": "🇪🇪", "CY": "🇨🇾", "MT": "🇲🇹", "PA": "🇵🇦", "CR": "🇨🇷",
}

# Cache for GeoIP lookups
_geoip_cache: Dict[str, Dict] = {}
_cache_file = Path("/etc/lobbyshift/geoip_cache.json")
_favorites_file = Path("/etc/lobbyshift/favorites.json")
_logs_file = Path("/etc/lobbyshift/connection_logs.json")


def _load_geoip_cache():
    """Load GeoIP cache from file"""
    global _geoip_cache
    try:
        if _cache_file.exists():
            _geoip_cache = json.loads(_cache_file.read_text())
    except:
        _geoip_cache = {}


def _save_geoip_cache():
    """Save GeoIP cache to file"""
    try:
        _cache_file.parent.mkdir(parents=True, exist_ok=True)
        _cache_file.write_text(json.dumps(_geoip_cache))
    except:
        pass


def _resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP address"""
    try:
        return socket.gethostbyname(hostname)
    except:
        return None


def lookup_geoip(ip_or_hostname: str) -> Dict:
    """Lookup country for an IP address using ip-api.com"""
    global _geoip_cache
    
    # Load cache on first call
    if not _geoip_cache:
        _load_geoip_cache()
    
    # Extract IP if it's hostname:port format
    host = ip_or_hostname.split(":")[0]
    
    # Check if it's a hostname and resolve it
    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
        resolved_ip = _resolve_hostname(host)
        if resolved_ip:
            host = resolved_ip
        else:
            return {"code": "??", "name": "Unknown", "flag": "🌍"}
    
    # Check cache
    if host in _geoip_cache:
        return _geoip_cache[host]
    
    # Query ip-api.com (free, no API key needed)
    try:
        url = f"http://ip-api.com/json/{host}?fields=status,countryCode,country"
        req = urllib.request.Request(url, headers={"User-Agent": "LobbyShift/1.0"})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if data.get("status") == "success":
                code = data.get("countryCode", "??")
                result = {
                    "code": code,
                    "name": data.get("country", "Unknown"),
                    "flag": COUNTRY_FLAGS.get(code, "🌍")
                }
            else:
                result = {"code": "??", "name": "Unknown", "flag": "🌍"}
    except Exception as e:
        print(f"GeoIP lookup failed for {host}: {e}")
        result = {"code": "??", "name": "Unknown", "flag": "🌍"}
    
    # Cache result
    _geoip_cache[host] = result
    _save_geoip_cache()
    
    return result


class WireGuardManager:
    """Manages WireGuard VPN connections"""
    
    def __init__(
        self,
        configs_dir: Path,
        interface_name: str = "lobbyshift",
        allowed_ips: List[str] = None
    ):
        self.configs_dir = Path(configs_dir)
        self.interface_name = interface_name
        self.allowed_ips = allowed_ips or ["185.34.0.0/16"]
        self.active_config: Optional[str] = None
        
        # Ensure configs directory exists
        self.configs_dir.mkdir(parents=True, exist_ok=True)
    
    async def _run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if check and process.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{stderr.decode()}")
        
        return subprocess.CompletedProcess(
            cmd, process.returncode,
            stdout.decode(), stderr.decode()
        )
    
    def _get_config_path(self, name: str) -> Path:
        """Get full path to a config file"""
        # Remove .conf extension if present
        name = name.replace('.conf', '')
        return self.configs_dir / f"{name}.conf"
    
    def _modify_config_for_split_tunnel(self, content: str) -> str:
        """Modify a WireGuard config for split tunneling"""
        lines = content.split('\n')
        modified_lines = []
        in_peer_section = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track sections
            if stripped.startswith('[Peer]'):
                in_peer_section = True
            elif stripped.startswith('[') and stripped.endswith(']'):
                in_peer_section = False
            
            # Modify AllowedIPs in Peer section
            if in_peer_section and stripped.lower().startswith('allowedips'):
                # Replace with our specific IPs
                allowed_ips_str = ', '.join(self.allowed_ips)
                modified_lines.append(f"AllowedIPs = {allowed_ips_str}")
                continue
            
            # Comment out DNS to prevent system DNS changes
            if stripped.lower().startswith('dns'):
                modified_lines.append(f"# {line}")
                continue
            
            modified_lines.append(line)
        
        return '\n'.join(modified_lines)
    
    async def save_config(self, name: str, content: str) -> Path:
        """Save a new WireGuard config with split tunnel modifications"""
        # Sanitize name
        name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        
        # Modify for split tunneling
        modified_content = self._modify_config_for_split_tunnel(content)
        
        # Save
        config_path = self._get_config_path(name)
        config_path.write_text(modified_content)
        config_path.chmod(0o600)
        
        return config_path
    
    async def update_config(self, name: str, content: str) -> None:
        """Update an existing config"""
        config_path = self._get_config_path(name)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {name}")
        
        # Modify for split tunneling
        modified_content = self._modify_config_for_split_tunnel(content)
        
        config_path.write_text(modified_content)
        config_path.chmod(0o600)
        
        # Restart if this config is active
        if self.active_config == name:
            await self.restart()
    
    def get_config_content(self, name: str, sanitize: bool = False) -> str:
        """Get config content, optionally sanitizing sensitive data"""
        config_path = self._get_config_path(name)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {name}")
        
        content = config_path.read_text()
        
        if sanitize:
            # Remove private key
            content = re.sub(
                r'(PrivateKey\s*=\s*)[^\n]+',
                r'\1[HIDDEN]',
                content
            )
        
        return content
    
    def delete_config(self, name: str) -> None:
        """Delete a config file"""
        config_path = self._get_config_path(name)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {name}")
        
        config_path.unlink()
    
    def list_configs(self) -> List[Dict]:
        """List all available configs"""
        configs = []
        favorites = self.get_favorites()
        
        for conf_file in sorted(self.configs_dir.glob("*.conf")):
            name = conf_file.stem
            stat = conf_file.stat()
            content = conf_file.read_text()
            
            # Try to extract endpoint from config
            endpoint_match = re.search(r'Endpoint\s*=\s*([^\s]+)', content)
            endpoint = endpoint_match.group(1) if endpoint_match else "Unknown"
            
            # Get country from IP via GeoIP lookup
            if endpoint != "Unknown":
                country = lookup_geoip(endpoint)
            else:
                country = {"code": "??", "name": "Unknown", "flag": "🌍"}
            
            configs.append({
                "name": name,
                "endpoint": endpoint,
                "country": country,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "active": name == self.active_config,
                "favorite": name in favorites
            })
        
        # Sort: favorites first, then alphabetically
        configs.sort(key=lambda x: (not x["favorite"], x["name"].lower()))
        
        return configs
    
    async def start(self, config_name: str) -> None:
        """Start WireGuard with a specific config"""
        config_path = self._get_config_path(config_name)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_name}")
        
        # Stop if already running
        await self.stop()
        
        # Copy config to WireGuard directory with our interface name
        wg_config_path = Path(f"/etc/wireguard/{self.interface_name}.conf")
        wg_config_path.write_text(config_path.read_text())
        wg_config_path.chmod(0o600)
        
        # Start WireGuard
        await self._run_command(["wg-quick", "up", self.interface_name])
        
        self.active_config = config_name
        
        # Log connection
        content = config_path.read_text()
        endpoint_match = re.search(r'Endpoint\s*=\s*([^\s]+)', content)
        endpoint = endpoint_match.group(1) if endpoint_match else "Unknown"
        country = lookup_geoip(endpoint) if endpoint != "Unknown" else {"name": "Unknown"}
        self._log_connection("connected", config_name, f"{country.get('name', 'Unknown')} ({endpoint})")
        
        # Refresh iptables rules
        await self.refresh_iptables()
    
    async def stop(self) -> None:
        """Stop WireGuard"""
        was_active = self.active_config
        
        try:
            await self._run_command(
                ["wg-quick", "down", self.interface_name],
                check=False
            )
        except:
            pass
        
        # Log disconnection
        if was_active:
            self._log_connection("disconnected", was_active)
        
        self.active_config = None
    
    async def restart(self) -> None:
        """Restart WireGuard with current config"""
        if self.active_config:
            await self.start(self.active_config)
    
    async def switch(self, config_name: str) -> None:
        """Switch to a different config"""
        await self.start(config_name)
    
    async def get_status(self) -> Dict:
        """Get current WireGuard status"""
        status = {
            "active": False,
            "config": None,
            "interface": self.interface_name,
            "peer": None,
            "endpoint": None,
            "latest_handshake": None,
            "transfer_rx": 0,
            "transfer_tx": 0
        }
        
        # Check if interface exists
        try:
            result = await self._run_command(
                ["wg", "show", self.interface_name],
                check=False
            )
            
            if result.returncode == 0:
                status["active"] = True
                status["config"] = self.active_config
                
                output = result.stdout
                
                # Parse wg show output
                peer_match = re.search(r'peer:\s*(\S+)', output)
                if peer_match:
                    status["peer"] = peer_match.group(1)[:16] + "..."
                
                endpoint_match = re.search(r'endpoint:\s*(\S+)', output)
                if endpoint_match:
                    status["endpoint"] = endpoint_match.group(1)
                
                handshake_match = re.search(r'latest handshake:\s*(.+)', output)
                if handshake_match:
                    status["latest_handshake"] = handshake_match.group(1)
                
                transfer_match = re.search(r'transfer:\s*([\d.]+\s*\w+)\s*received,\s*([\d.]+\s*\w+)\s*sent', output)
                if transfer_match:
                    status["transfer_rx"] = transfer_match.group(1)
                    status["transfer_tx"] = transfer_match.group(2)
        
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    async def refresh_iptables(self) -> None:
        """Refresh iptables rules for the VPN"""
        iptables_script = Path("/etc/lobbyshift/iptables-rules.sh")
        
        if iptables_script.exists():
            await self._run_command(["bash", str(iptables_script)])
    
    # =========================================================================
    # Favorites Management
    # =========================================================================
    
    def get_favorites(self) -> List[str]:
        """Get list of favorite config names"""
        try:
            if _favorites_file.exists():
                return json.loads(_favorites_file.read_text())
        except:
            pass
        return []
    
    def add_favorite(self, name: str) -> None:
        """Add a config to favorites"""
        favorites = self.get_favorites()
        if name not in favorites:
            favorites.append(name)
            _favorites_file.parent.mkdir(parents=True, exist_ok=True)
            _favorites_file.write_text(json.dumps(favorites))
    
    def remove_favorite(self, name: str) -> None:
        """Remove a config from favorites"""
        favorites = self.get_favorites()
        if name in favorites:
            favorites.remove(name)
            _favorites_file.write_text(json.dumps(favorites))
    
    def is_favorite(self, name: str) -> bool:
        """Check if a config is a favorite"""
        return name in self.get_favorites()
    
    # =========================================================================
    # Connection Logging
    # =========================================================================
    
    def _log_connection(self, action: str, config_name: str = None, details: str = None) -> None:
        """Log a connection event"""
        logs = self.get_connection_logs()
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "config": config_name,
            "details": details
        }
        
        logs.insert(0, log_entry)  # Newest first
        
        # Keep only last 100 entries
        logs = logs[:100]
        
        try:
            _logs_file.parent.mkdir(parents=True, exist_ok=True)
            _logs_file.write_text(json.dumps(logs, indent=2))
        except:
            pass
    
    def get_connection_logs(self) -> List[Dict]:
        """Get connection history"""
        try:
            if _logs_file.exists():
                return json.loads(_logs_file.read_text())
        except:
            pass
        return []
    
    def clear_connection_logs(self) -> None:
        """Clear all connection logs"""
        try:
            _logs_file.write_text("[]")
        except:
            pass
