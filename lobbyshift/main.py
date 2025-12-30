"""
LobbyShift - FastAPI Backend
"""

import os
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from .wireguard import WireGuardManager
from .config import Config, load_config

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = Path("/etc/lobbyshift")
CONFIGS_DIR = CONFIG_DIR / "configs"

# Global instances
config: Config = None
wg_manager: WireGuardManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global config, wg_manager
    
    # Startup
    config = load_config()
    wg_manager = WireGuardManager(
        configs_dir=CONFIGS_DIR,
        interface_name="lobbyshift",
        allowed_ips=config.allowed_ips
    )
    
    # Auto-start if configured
    if config.autostart and config.autostart_config:
        try:
            await wg_manager.start(config.autostart_config)
        except Exception as e:
            print(f"Auto-start failed: {e}")
    
    yield
    
    # Shutdown
    await wg_manager.stop()


# Create FastAPI app
app = FastAPI(
    title="LobbyShift",
    description="Self-hosted CoD Lobby Optimizer",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    # Create static dir if it doesn't exist
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# =============================================================================
# Web Interface
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main web interface"""
    status = await wg_manager.get_status()
    configs = wg_manager.list_configs()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "status": status,
        "configs": configs,
        "server_ip": config.server_ip,
        "web_port": config.web_port
    })


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/api/status")
async def api_status():
    """Get current VPN status"""
    status = await wg_manager.get_status()
    
    # Add country info if active
    if status.get("active") and status.get("config"):
        configs = wg_manager.list_configs()
        for cfg in configs:
            if cfg["name"] == status["config"]:
                status["country"] = cfg.get("country")
                break
    
    return status


@app.get("/api/configs")
async def api_list_configs():
    """List all available configs"""
    configs = wg_manager.list_configs()
    return {"configs": configs}


@app.post("/api/configs")
async def api_upload_config(file: UploadFile = File(...)):
    """Upload a new WireGuard config"""
    if not file.filename.endswith('.conf'):
        raise HTTPException(status_code=400, detail="File must be a .conf file")
    
    content = await file.read()
    
    try:
        config_name = file.filename.replace('.conf', '')
        saved_path = await wg_manager.save_config(config_name, content.decode('utf-8'))
        return {"message": "Config uploaded", "name": config_name, "path": str(saved_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/configs/{name}")
async def api_get_config(name: str):
    """Get config content (sanitized - no private keys)"""
    try:
        content = wg_manager.get_config_content(name, sanitize=True)
        return {"name": name, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config not found")


@app.put("/api/configs/{name}")
async def api_update_config(name: str, request: Request):
    """Update config content"""
    body = await request.json()
    content = body.get("content")
    
    if not content:
        raise HTTPException(status_code=400, detail="Content required")
    
    try:
        await wg_manager.update_config(name, content)
        return {"message": "Config updated", "name": name}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/configs/{name}")
async def api_delete_config(name: str):
    """Delete a config"""
    try:
        # Stop if this config is active
        status = await wg_manager.get_status()
        if status.get("active") and status.get("config") == name:
            await wg_manager.stop()
        
        wg_manager.delete_config(name)
        return {"message": "Config deleted", "name": name}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config not found")


@app.post("/api/switch/{name}")
async def api_switch_config(name: str):
    """Switch to a different config"""
    try:
        await wg_manager.switch(name)
        return {"message": f"Switched to {name}", "config": name}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/up")
async def api_start_vpn():
    """Start VPN with current or default config"""
    status = await wg_manager.get_status()
    
    if status.get("active"):
        return {"message": "VPN already running", "status": status}
    
    # Get first available config
    configs = wg_manager.list_configs()
    if not configs:
        raise HTTPException(status_code=400, detail="No configs available")
    
    config_name = configs[0]["name"]
    await wg_manager.start(config_name)
    
    return {"message": "VPN started", "config": config_name}


@app.post("/api/down")
async def api_stop_vpn():
    """Stop VPN"""
    await wg_manager.stop()
    return {"message": "VPN stopped"}


@app.post("/api/refresh-iptables")
async def api_refresh_iptables():
    """Refresh iptables rules"""
    try:
        await wg_manager.refresh_iptables()
        return {"message": "iptables refreshed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/favorites")
async def api_get_favorites():
    """Get list of favorite configs"""
    favorites = wg_manager.get_favorites()
    return {"favorites": favorites}


@app.post("/api/favorites/{name}")
async def api_add_favorite(name: str):
    """Add config to favorites"""
    wg_manager.add_favorite(name)
    return {"message": f"Added {name} to favorites"}


@app.delete("/api/favorites/{name}")
async def api_remove_favorite(name: str):
    """Remove config from favorites"""
    wg_manager.remove_favorite(name)
    return {"message": f"Removed {name} from favorites"}


@app.get("/api/logs")
async def api_get_logs():
    """Get connection history logs"""
    logs = wg_manager.get_connection_logs()
    return {"logs": logs}


@app.delete("/api/logs")
async def api_clear_logs():
    """Clear connection history"""
    wg_manager.clear_connection_logs()
    return {"message": "Logs cleared"}


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the application"""
    cfg = load_config()
    uvicorn.run(
        "lobbyshift.main:app",
        host=cfg.web_host,
        port=cfg.web_port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
