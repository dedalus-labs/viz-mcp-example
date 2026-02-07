# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Test client for minimal_viz_server.py using Dedalus SDK.

The LLM is the MCP client. It calls tools, receives data/charts, and reasons about them.
Vision-capable models can "see" chart images returned by get_chart().

Usage:
    uv run client.py

Environment variables:
    DEDALUS_API_KEY: Your Dedalus API key (required)
    DEDALUS_BASE_URL: Dedalus API base URL (default: https://api.dedaluslabs.ai)
"""

import os

from dedalus_labs import Dedalus, DedalusRunner
from dotenv import load_dotenv


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


# From your environment
api_key = get_env("DEDALUS_API_KEY")
base_url = get_env("DEDALUS_BASE_URL")


def main() -> None:
    """Run viz agent."""
    client = Dedalus(api_key=api_key, base_url=base_url)
    runner = DedalusRunner(client)

    print("Testing: push data -> generate chart -> describe chart\n")

    response = runner.run(
        model="openai/gpt-4.1-mini",  # Fast vision model.
        input="""
            1. Clear any existing data
            2. Push these temperature values: 20, 22, 25, 24, 28, 30, 27
            3. Generate a chart titled "Temperature Readings"
            4. Look at the chart and describe the trend you see
            """,
        mcp_servers=["http://localhost:8000/mcp"],  # Replace with Dedalus slug or MCP URL.
    )
    print(response.output)


if __name__ == "__main__":
    main()
