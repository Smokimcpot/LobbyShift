# Contributing to LobbyShift

Thanks for your interest in contributing! 🎮

## How to Contribute

### Reporting Bugs

- Check if the issue already exists
- Include your OS version, Python version, and relevant logs
- Describe steps to reproduce

### Suggesting Features

- Open an issue with `[Feature]` prefix
- Describe the use case and expected behavior

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test locally
5. Commit with clear messages
6. Push and create a PR

## Development Setup

```bash
# Clone your fork
git clone https://github.com/Smokimcpot/LobbyShift.git
cd LobbyShift

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally (requires root for WireGuard)
sudo python -m lobbyshift.main
```

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to functions
- Keep functions small and focused

## Testing

```bash
# Run tests (coming soon)
pytest
```

## Areas We Need Help

- 🌍 More VPN provider templates
- 📊 Lobby tracking integration (cod.tracker.gg API)
- 🐳 Docker support
- 📱 Mobile-friendly UI improvements
- 📝 Documentation and translations
- 🧪 Test coverage

## Code of Conduct

Be respectful. We're all here to have fun gaming with fair lobbies.

## Questions?

Open an issue or join discussions.
