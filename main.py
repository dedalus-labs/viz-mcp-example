# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Minimal MCP server for data visualization with LLMs.

Pattern: LLM calls tools to read/write data and generate charts.
The LLM "sees" the results (text or images) and reasons about them.

Usage:
    uv run python main.py

Environment variables:
    REDIS_URL: Redis connection string (required, or uses default test instance)

Tools:
    - push(value, label) - add a data point
    - get_metrics() - get current data as JSON
    - get_chart() - render data as PNG chart (for vision LLMs)
    - clear() - reset all data
"""

import asyncio
import base64
from datetime import datetime
from io import BytesIO
import json
import os
from typing import Final

from dotenv import load_dotenv
import redis.asyncio as redis

from dedalus_mcp import MCPServer, resource, tool
from dedalus_mcp.types import ImageContent


load_dotenv()


# --- Environment ---


class MissingEnvError(ValueError):
    """Required environment variable not set."""


def get_env(key: str, default: str | None = None) -> str:
    """Get env var, raise if required and missing."""
    val = os.getenv(key, default)
    if val is None:
        raise MissingEnvError(key)
    return val


REDIS_URL = get_env(key="REDIS_URL")
STATE_KEY: Final[str] = "viz_state"


# --- Redis backend ---

server = MCPServer("viz")
pool = redis.ConnectionPool.from_url(REDIS_URL)


# !! --- This can be something else, like a webhook or a database call --- !!
async def get_state() -> dict:
    client = redis.Redis(connection_pool=pool)
    try:
        data = await client.get(STATE_KEY)
        if data:
            return json.loads(data)
        return {"metrics": [], "last_updated": None}
    finally:
        await client.aclose()


# !! --- This can be something else, like a webhook or a database call --- !!
async def set_state(state: dict) -> None:
    client = redis.Redis(connection_pool=pool)
    try:
        await client.set(STATE_KEY, json.dumps(state))
    finally:
        await client.aclose()


# --- Tools ---


@tool(description="Add a data point to the metrics")
async def push(value: float, label: str = "default") -> dict:
    """Push a new data point. The LLM can call this to record measurements."""
    state = await get_state()
    entry = {"value": value, "label": label, "ts": datetime.now().isoformat()}
    state["metrics"].append(entry)
    state["metrics"] = state["metrics"][-100:]  # Keep last 100
    state["last_updated"] = entry["ts"]
    await set_state(state)
    return {"pushed": entry, "total_points": len(state["metrics"])}


@tool(description="Get current metrics as JSON")
async def get_metrics() -> dict:
    """Get all metrics. Returns JSON that the LLM can analyze."""
    state = await get_state()
    return {"metrics": state["metrics"], "count": len(state["metrics"]), "last_updated": state["last_updated"]}


@tool(description="Render metrics as a line chart image (PNG)")
async def get_chart(title: str = "Metrics", width: int = 800, height: int = 400) -> ImageContent | dict:
    """Generate a chart visualization. Returns PNG image for vision LLMs.

    Args:
        title: Chart title
        width: Image width in pixels
        height: Image height in pixels
    """
    try:
        import matplotlib as mpl  # noqa: PLC0415

        mpl.use("Agg")  # Non-interactive backend for bursty Dedalus MCP servers.
        import matplotlib.pyplot as plt  # noqa: PLC0415
    except ImportError:
        return {"error": "matplotlib not installed. Run: uv pip install matplotlib"}

    state = await get_state()
    metrics = state["metrics"]

    if not metrics:
        return {"error": "No data to chart. Use push() to add data points."}

    # Extract data
    values = [m["value"] for m in metrics]
    labels = [m["label"] for m in metrics]
    timestamps = list(range(len(values)))  # Simple x-axis

    # Create chart
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    # Group by label and plot each series
    unique_labels = list(set(labels))
    for lbl in unique_labels:
        indices = [i for i, lab in enumerate(labels) if lab == lbl]
        xs = [timestamps[i] for i in indices]
        ys = [values[i] for i in indices]
        ax.plot(xs, ys, marker="o", label=lbl, linewidth=2, markersize=4)

    ax.set_title(title)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Value")
    ax.legend()
    ax.grid(alpha=0.3)

    # Save to bytes
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    img = ImageContent(type="image", data=img_base64, mimeType="image/png")
    return img


@tool(description="Clear all metrics data")
async def clear() -> dict:
    """Reset metrics to empty. Use when starting fresh."""
    await set_state({"metrics": [], "last_updated": None})
    return {"cleared": True}


# --- Resource (for polling/direct reads) ---


@resource(uri="data://metrics", description="Current metrics snapshot")
async def read_metrics() -> dict:
    """Read current state as a resource."""
    return await get_state()


# Collect all tools and resources for your MCP server!
server.collect(push, get_metrics, get_chart, clear, read_metrics)


if __name__ == "__main__":
    """
    Minimal Viz MCP Server

    Environment:
      REDIS_URL:          {REDIS_URL[:40]}...

    MCP endpoint:
      <Your Dedalus MCP server slug or MCP server URL here>

    Tools:
      push(value, label)     - add data point
      get_metrics()          - get JSON data
      get_chart(title)       - render PNG chart
      clear()                - reset data

    Resource:
      data://metrics         - current state
    """

    asyncio.run(server.serve())
