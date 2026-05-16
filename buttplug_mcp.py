"""
buttplug-mcp-py
A Python MCP server for controlling Buttplug.io devices via AI (Claude Desktop, etc.)
Actually works end-to-end, unlike the original Go implementation.

Author: Wanderer-the-coder
GitHub: https://github.com/Wanderer-the-coder/buttplug-mcp-py
"""

import asyncio
import sys
import json
import logging
from buttplug import Client, WebsocketConnector

# ─── CONFIG ────────────────────────────────────────────────────────────────────
WS_PORT = 12345          # Intiface Central websocket port
WS_HOST = "localhost"    # Intiface Central host
SCAN_DURATION = 2        # Seconds to scan for devices on startup
# ───────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("buttplug-mcp-py")

# Global state
bp_client: Client = None
bp_devices: dict = {}


async def connect_and_scan():
    """Connect to Intiface Central and scan for devices."""
    global bp_client, bp_devices

    bp_client = Client("buttplug-mcp-py")
    connector = WebsocketConnector(f"ws://{WS_HOST}:{WS_PORT}")

    try:
        await bp_client.connect(connector)
        logger.info(f"Connected to Intiface Central at ws://{WS_HOST}:{WS_PORT}")
    except Exception as e:
        logger.error(f"Failed to connect to Intiface Central: {e}")
        logger.error("Make sure Intiface Central is running and the port is correct.")
        sys.exit(1)

    await bp_client.start_scanning()
    await asyncio.sleep(SCAN_DURATION)
    await bp_client.stop_scanning()

    bp_devices = {dev.index: dev for dev in bp_client.devices.values()}

    logger.info(f"Found {len(bp_devices)} device(s):")
    for idx, dev in bp_devices.items():
        logger.info(f"  [{idx}] {dev.name} — {len(dev.actuators)} actuator(s)")


def list_devices_json() -> str:
    """Return a JSON string of all connected devices."""
    devices = []
    for idx, dev in bp_devices.items():
        devices.append({
            "index": idx,
            "name": dev.name,
            "actuators": len(dev.actuators),
        })
    return json.dumps(devices, indent=2)


async def vibrate_device(device_id: int, strength: float, motor: int = 0) -> dict:
    """Vibrate a device actuator at a given strength."""
    if device_id not in bp_devices:
        return {"success": False, "error": f"Device id {device_id} not found. Connected: {list(bp_devices.keys())}"}

    device = bp_devices[device_id]

    if motor < 0 or motor >= len(device.actuators):
        return {"success": False, "error": f"Motor {motor} not found. Device has {len(device.actuators)} actuator(s)."}

    strength = max(0.0, min(1.0, strength))  # Clamp to [0.0, 1.0]

    await device.actuators[motor].command(strength)

    return {
        "success": True,
        "device_id": device_id,
        "device_name": device.name,
        "motor": motor,
        "strength": strength,
        "message": f"Device {device.name} (id={device_id}) vibrating at {strength * 100:.0f}%"
    }


async def stop_device(device_id: int) -> dict:
    """Stop all actuators on a device."""
    if device_id not in bp_devices:
        return {"success": False, "error": f"Device id {device_id} not found."}

    device = bp_devices[device_id]
    await device.stop()

    return {
        "success": True,
        "device_id": device_id,
        "device_name": device.name,
        "message": f"Device {device.name} (id={device_id}) stopped."
    }


async def stop_all_devices() -> dict:
    """Stop all connected devices."""
    stopped = []
    for idx, device in bp_devices.items():
        await device.stop()
        stopped.append(device.name)

    return {
        "success": True,
        "stopped": stopped,
        "message": f"Stopped {len(stopped)} device(s)."
    }


# ─── MCP STDIO PROTOCOL ────────────────────────────────────────────────────────

def send_response(response: dict):
    """Write a JSON-RPC response to stdout."""
    line = json.dumps(response)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def make_error(id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def make_result(id, result) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


TOOLS = [
    {
        "name": "list_devices",
        "description": "List all connected Buttplug.io devices with their index and actuator count.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "device_vibrate",
        "description": "Vibrate a device by index at a given strength. Strength is 0.0 (off) to 1.0 (full).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id":       {"type": "integer", "description": "Device index from list_devices"},
                "strength": {"type": "number",  "description": "Vibration strength: 0.0 to 1.0"},
                "motor":    {"type": "integer", "description": "Motor/actuator index (default: 0)"},
            },
            "required": ["id", "strength"]
        }
    },
    {
        "name": "device_stop",
        "description": "Stop all vibration on a specific device.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Device index from list_devices"},
            },
            "required": ["id"]
        }
    },
    {
        "name": "stop_all",
        "description": "Stop all connected devices immediately.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
]


async def handle_request(request: dict):
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        send_response(make_result(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "buttplug-mcp-py", "version": "1.0.0"}
        }))

    elif method == "notifications/initialized":
        pass  # No response needed

    elif method == "tools/list":
        send_response(make_result(req_id, {"tools": TOOLS}))

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "list_devices":
                result_text = list_devices_json()

            elif tool_name == "device_vibrate":
                device_id = int(args["id"])
                strength = float(args["strength"])
                motor = int(args.get("motor", 0))
                res = await vibrate_device(device_id, strength, motor)
                result_text = json.dumps(res)

            elif tool_name == "device_stop":
                device_id = int(args["id"])
                res = await stop_device(device_id)
                result_text = json.dumps(res)

            elif tool_name == "stop_all":
                res = await stop_all_devices()
                result_text = json.dumps(res)

            else:
                send_response(make_error(req_id, -32601, f"Unknown tool: {tool_name}"))
                return

            send_response(make_result(req_id, {
                "content": [{"type": "text", "text": result_text}]
            }))

        except Exception as e:
            send_response(make_error(req_id, -32603, str(e)))

    elif method == "resources/list":
        send_response(make_result(req_id, {"resources": []}))

    else:
        if req_id is not None:
            send_response(make_error(req_id, -32601, f"Method not found: {method}"))


async def main():
    logger.info("buttplug-mcp-py starting...")
    await connect_and_scan()
    logger.info("MCP server ready. Waiting for requests...")

    loop = asyncio.get_event_loop()

    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            request = json.loads(line)
            await handle_request(request)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
