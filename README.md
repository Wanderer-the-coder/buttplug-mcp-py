# buttplug-mcp-py

A Python MCP (Model Context Protocol) server for controlling [Buttplug.io](https://buttplug.io) devices via AI assistants like Claude Desktop.

> Actually works end-to-end, unlike the [original Go implementation](https://github.com/ConAcademy/buttplug-mcp).

---

## Requirements

- Python 3.10+
- [Intiface Central](https://intiface.com/central/) running on `ws://localhost:12345`
- [Claude Desktop](https://claude.ai/download) (or any MCP-compatible host)
- A [Buttplug.io-supported device](https://iostindex.com/)

---

## Installation

```bash
pip install -r requirements.txt
```

> **Note:** This server speaks MCP over stdio directly and does not require the Python `mcp` package.

---

## Setup

### 1. Start Intiface Central

Download and launch [Intiface Central](https://intiface.com/central/). Make sure your device is connected and the server is running on port `12345`.

### 2. Configure Claude Desktop

Find your Claude Desktop config file:

- **Windows (Store):** `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json`
- **Windows (Standard):** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following (adjust the path to where you saved `buttplug_mcp.py`):

```json
{
  "mcpServers": {
    "buttplug": {
      "command": "python",
      "args": ["C:\\Users\\YourName\\Downloads\\buttplug_mcp.py"]
    }
  }
}
```

### 3. Restart Claude Desktop

Claude will now have access to your Buttplug.io devices.

---

## Usage

Once set up, just talk to Claude:

- *"List my connected devices"*
- *"Vibrate device 1 at 50% strength"*
- *"Stop all devices"*
- *"Set motor 0 on device 1 to 80%"*

---

## Available MCP Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_devices` | — | List all connected devices |
| `device_vibrate` | `id`, `strength`, `motor?` | Vibrate a device (strength: 0.0–1.0) |
| `device_stop` | `id` | Stop a specific device |
| `stop_all` | — | Stop all devices immediately |

---

## Configuration

Edit the top of `buttplug_mcp.py` to change defaults:

```python
WS_PORT = 12345       # Intiface Central port
WS_HOST = "localhost" # Intiface Central host
SCAN_DURATION = 2     # Seconds to scan for devices on startup
```

---

## Safety

This project controls physical hardware.

- Keep Intiface Central bound to `localhost` — do not expose it to the public internet
- Always keep a manual stop method available
- Use `stop_all` as a panic command if needed
- Start with low strengths when testing a new device

---

## Why Python instead of Go?

The original [buttplug-mcp](https://github.com/ConAcademy/buttplug-mcp) is written in Go and uses the `go-buttplug` library, which has known connection stability issues. The author themselves noted it was "unstable and frustrating" and had not been tested end-to-end.

This Python implementation uses the `buttplug-py` library, which provides a more stable and straightforward API. It has been tested and confirmed working end-to-end.

---

## License

MIT — [Wanderer-the-coder](https://github.com/Wanderer-the-coder)
