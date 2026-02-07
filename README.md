# Viz MCP Example

MCP server that renders visuals for vision LLMs.

## Security

Since this server takes a sensitive credential as an environment variable, it's recommended to keep it as a private server on the [Dedalus platform](https://dedaluslabs.ai).

If you want to allow arbitrary tokens passed in, please visit our [docs](https://docs.dedaluslabs.ai) at look for "DAuth" (Dedalus Auth) and "bearer auth" (navigate quickly with Cmd+K).

## Setup

```bash
cp .env.example .env
# Fill in REDIS_URL and DEDALUS_API_KEY
```

## Run

```bash
# Terminal 1: server
python3 run server.py

# Terminal 2: client
python3 run client.py
```

## Tools

| Tool | Description |
|------|-------------|
| `push(value, label)` | Add data point |
| `get_metrics()` | Get JSON data |
| `get_chart(title)` | Render PNG (vision LLMs see this) |
| `clear()` | Reset data |

## How it works

1. Client sends instruction to Dedalus agent
2. Agent calls tools on server (`push`, `get_chart`, etc.)
3. `get_chart()` returns `ImageContent` — vision models "see" the PNG
4. Agent describes what it sees

## Data backend

`get_state()` and `set_state()` in `main.py` are swappable. This example uses Redis, but you can replace with:

- Webhook calls to your backend
- Another database (Postgres, DynamoDB, etc.)
- Any external service

MCP servers hosted on the Dedalus Hobby Tier are limited to bursty servers. This means that server state will not persist across sessions, so you will need to provide your own external storage.

> [!NOTE]
> Vision LLMs will be able to see the chart. In trying to keep this example simple, the agent will only be able to output its observations instead of serializing the image to the user. If you need the save its response:
> - **External storage**: Have `get_chart()` upload PNG to S3/R2/your backend of choice.
> - **Vision agent as tool**: Call a vision model as a @tool (wrap its invocation in a function), return description + base64 data or other creative strategy here.
> - **Direct MCP client**: Bypass the LLM with `MCPClient` from the `dedalus-mcp` framework (note: MCPClient is a non-DAuth client), decode base64 yourself.

## Requirements

- External state store (Redis, Upstash, webhook, etc.)
- `matplotlib` for charts
