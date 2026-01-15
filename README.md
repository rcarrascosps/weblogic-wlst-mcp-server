# WLST MCP Server

A Model Context Protocol (MCP) server for Oracle WebLogic Server administration using WLST (WebLogic Scripting Tool).

## Overview

This MCP server provides a comprehensive set of tools for managing Oracle WebLogic Server domains, including server lifecycle management, application deployment, monitoring, and diagnostics.

## Project Structure

```
wlst-mcp/
├── src/
│   └── wlst_mcp.py          # Main MCP server implementation
├── README.md                 # This file - main documentation
├── ARCHITECTURE.md           # System architecture diagrams
├── INSTALLATION.md           # Prerequisites and installation guide
├── INTEGRATION.md            # Claude Desktop & Claude Code setup
├── EXAMPLES.md               # Usage examples and custom scripts
├── requirements.txt          # Python dependencies
├── LICENSE                   # Apache License 2.0
└── .gitignore               # Git ignore patterns
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export WLST_ADMIN_URL=t3://localhost:7001
   export WLST_USERNAME=weblogic
   export WLST_PASSWORD=your_password
   ```

3. **Run the MCP server:**
   ```bash
   python src/wlst_mcp.py
   ```

4. **Integrate with Claude:** See [INTEGRATION.md](INTEGRATION.md) for detailed setup instructions.

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and component diagrams |
| [INSTALLATION.md](INSTALLATION.md) | Prerequisites, installation, security configuration |
| [INTEGRATION.md](INTEGRATION.md) | Claude Desktop & Claude Code integration |
| [EXAMPLES.md](EXAMPLES.md) | Usage examples and custom WLST scripts |

## Features

- **Server Management**: Start, stop, restart, and monitor WebLogic servers
- **Application Deployment**: Deploy, undeploy, and list applications
- **Monitoring**: Real-time metrics for JVM, threads, JDBC, and JMS
- **Diagnostics**: Thread dumps and health checks
- **Resource Management**: JDBC datasources and JMS resources
- **Custom Scripting**: Execute custom WLST/Jython scripts

## Available Tools

### Connection & Discovery

| Tool | Description |
|------|-------------|
| `wlst_test_connection` | Test connectivity to a WebLogic Admin Server |
| `wlst_list_servers` | List all servers in a WebLogic domain with their status |

### Server Lifecycle

| Tool | Description |
|------|-------------|
| `wlst_start_server` | Start a managed server |
| `wlst_stop_server` | Stop a managed server (supports force option) |
| `wlst_restart_server` | Restart a managed server |

### Application Management

| Tool | Description |
|------|-------------|
| `wlst_deploy` | Deploy an application (WAR, EAR, JAR) |
| `wlst_undeploy` | Undeploy an application |
| `wlst_start_application` | Start a deployed application |
| `wlst_stop_application` | Stop a running application (without undeploying) |
| `wlst_redeploy_application` | Redeploy an application in place |
| `wlst_list_applications` | List all deployed applications |

### Monitoring & Metrics

| Tool | Description |
|------|-------------|
| `wlst_server_health` | Get health status of WebLogic servers |
| `wlst_server_metrics` | Get detailed metrics (JVM, threads, JDBC, JMS) |

### Resource Management

| Tool | Description |
|------|-------------|
| `wlst_list_datasources` | List all JDBC datasources |
| `wlst_list_jms_resources` | List JMS servers, modules, queues, and topics |

### Diagnostics

| Tool | Description |
|------|-------------|
| `wlst_thread_dump` | Capture thread dump for debugging |
| `wlst_execute_script` | Execute custom WLST/Jython scripts |

## Tool Reference

### wlst_test_connection

Test connectivity to a WebLogic Admin Server.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `admin_url` | string | No | Admin Server URL (e.g., `t3://localhost:7001`). Uses `WLST_ADMIN_URL` env var if not provided |
| `username` | string | No | WebLogic admin username. Uses `WLST_USERNAME` env var if not provided |
| `password` | string | No | WebLogic admin password. Uses `WLST_PASSWORD` env var if not provided |
| `timeout` | integer | No | Connection timeout in seconds (10-600, default: 120) |

---

### wlst_list_servers

List all servers in a WebLogic domain with their status.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `response_format` | string | No | Output format: `markdown` or `json` (default: `markdown`) |

---

### wlst_start_server

Start a managed server in a WebLogic domain.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_name` | string | **Yes** | Name of the managed server to start |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Operation timeout in seconds (10-600, default: 120) |

---

### wlst_stop_server

Stop a managed server in a WebLogic domain. Supports two shutdown modes:

- **Graceful shutdown** (default): Waits for active sessions to complete before stopping. This is safer for production environments but takes longer.
- **Force shutdown**: Stops the server immediately without waiting for sessions. Use when you need to stop quickly or the server is unresponsive.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_name` | string | **Yes** | Name of the managed server to stop |
| `force` | boolean | No | Force shutdown (immediate). If `false`, performs graceful shutdown waiting for sessions to complete. Default: `false` |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Operation timeout in seconds. Graceful shutdown may need longer timeout. (10-600, default: 300) |

**Shutdown Modes Comparison:**
| Mode | Parameter | Behavior | Use Case |
|------|-----------|----------|----------|
| Graceful | `force: false` | Waits for sessions to complete | Production, scheduled maintenance |
| Force | `force: true` | Immediate stop, sessions terminated | Emergency, unresponsive server |

---

### wlst_restart_server

Restart a managed server in a WebLogic domain. Performs a stop followed by a start.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_name` | string | **Yes** | Name of the managed server to restart |
| `force` | boolean | No | Force shutdown during restart. If `false`, performs graceful shutdown waiting for sessions. Default: `false` |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Operation timeout in seconds. Graceful restart may need longer timeout. (10-600, default: 300) |

---

### wlst_deploy

Deploy an application to WebLogic Server.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | **Yes** | Application name |
| `app_path` | string | **Yes** | Path to the application archive (WAR, EAR, JAR) |
| `targets` | string | No | Comma-separated list of target servers/clusters |
| `stage_mode` | string | No | Deployment stage mode: `stage`, `nostage`, or `external_stage` (default: `stage`) |
| `plan_path` | string | No | Path to deployment plan XML |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |

---

### wlst_undeploy

Undeploy an application from WebLogic Server.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | **Yes** | Name of the application to undeploy |
| `targets` | string | No | Comma-separated list of target servers/clusters |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Operation timeout (10-600, default: 120) |

---

### wlst_start_application

Start a deployed application in WebLogic Server. The application must be already deployed but in a stopped (STATE_PREPARED) state.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | **Yes** | Name of the application to start |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Operation timeout in seconds (10-600, default: 120) |

---

### wlst_stop_application

Stop a running application in WebLogic Server without undeploying it. The application transitions from STATE_ACTIVE to STATE_PREPARED, allowing it to be started again later.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | **Yes** | Name of the application to stop |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Operation timeout in seconds (10-600, default: 120) |

**Application States:**
| State | Description |
|-------|-------------|
| `STATE_ACTIVE` | Application is running and serving requests |
| `STATE_PREPARED` | Application is deployed but stopped (not serving requests) |

---

### wlst_redeploy_application

Redeploy an application in WebLogic Server. This updates the application in place without changing its configuration or targets. Useful for updating application code without a full undeploy/deploy cycle.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | **Yes** | Name of the application to redeploy |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Operation timeout in seconds (10-600, default: 120) |

---

### wlst_list_applications

List all deployed applications in a WebLogic domain.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `response_format` | string | No | Output format: `markdown` or `json` (default: `markdown`) |

---

### wlst_server_health

Get health status of WebLogic servers.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_name` | string | No | Specific server name (all servers if not specified) |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `response_format` | string | No | Output format: `markdown` or `json` (default: `markdown`) |

---

### wlst_server_metrics

Get detailed metrics for a WebLogic server.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_name` | string | **Yes** | Server name to get metrics for |
| `metric_type` | string | No | Type of metrics: `all`, `jvm`, `threads`, `jdbc`, `jms` (default: `all`) |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `response_format` | string | No | Output format: `markdown` or `json` (default: `markdown`) |

---

### wlst_list_datasources

List all JDBC datasources in a WebLogic domain.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `response_format` | string | No | Output format: `markdown` or `json` (default: `markdown`) |

---

### wlst_list_jms_resources

List all JMS resources in a WebLogic domain.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `response_format` | string | No | Output format: `markdown` or `json` (default: `markdown`) |

---

### wlst_thread_dump

Get a thread dump from a WebLogic server for debugging.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_name` | string | **Yes** | Server name to get thread dump from |
| `admin_url` | string | No | Admin Server URL |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |

---

### wlst_execute_script

Execute a custom WLST/Jython script.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `script` | string | **Yes** | WLST/Jython script to execute |
| `admin_url` | string | No | Admin Server URL (optional for offline scripts) |
| `username` | string | No | WebLogic admin username |
| `password` | string | No | WebLogic admin password |
| `timeout` | integer | No | Script execution timeout (10-1800, default: 120) |

## Configuration & Environment Variables

### How Credentials Are Resolved

The MCP server uses a **fallback mechanism** to resolve connection parameters. For each parameter, it checks in the following order:

```
1. Tool parameter (if provided) → 2. Environment variable → 3. Error (if required)
```

This means:
- If you provide a parameter in the tool call, it will be used
- If the parameter is not provided, the environment variable is used as default
- If neither is available, an error is returned for required parameters

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `WLST_ADMIN_URL` | WebLogic Admin Server URL (protocol://host:port) | `t3://localhost:7001` |
| `WLST_USERNAME` | WebLogic admin username | `weblogic` |
| `WLST_PASSWORD` | WebLogic admin password | `welcome1` |

### URL Format

The `WLST_ADMIN_URL` must follow this format:

```
<protocol>://<host>:<port>
```

| Component | Description | Examples |
|-----------|-------------|----------|
| `protocol` | Connection protocol | `t3`, `t3s`, `http`, `https` |
| `host` | Admin Server hostname or IP | `localhost`, `192.168.1.100`, `admin.example.com` |
| `port` | Admin Server listen port | `7001` (default), `7002` (SSL) |

**Examples:**
```bash
# Local development (non-SSL)
WLST_ADMIN_URL=t3://localhost:7001

# Local development (SSL)
WLST_ADMIN_URL=t3s://localhost:7002

# Remote server
WLST_ADMIN_URL=t3s://weblogic-admin.example.com:7002

# Using IP address
WLST_ADMIN_URL=t3://192.168.1.100:7001
```

### Configuration Examples

#### Option 1: Environment Variables (Recommended)

Set environment variables before starting the MCP server:

**Linux/macOS:**
```bash
export WLST_ADMIN_URL=t3://localhost:7001
export WLST_USERNAME=weblogic
export WLST_PASSWORD=your_password
```

**Windows (Command Prompt):**
```cmd
set WLST_ADMIN_URL=t3://localhost:7001
set WLST_USERNAME=weblogic
set WLST_PASSWORD=your_password
```

**Windows (PowerShell):**
```powershell
$env:WLST_ADMIN_URL = "t3://localhost:7001"
$env:WLST_USERNAME = "weblogic"
$env:WLST_PASSWORD = "your_password"
```

Once configured, you can call tools without specifying connection parameters:

```json
{
  "tool": "wlst_list_servers",
  "params": {}
}
```

#### Option 2: Tool Parameters (Override)

You can override environment variables by passing parameters directly:

```json
{
  "tool": "wlst_list_servers",
  "params": {
    "admin_url": "t3://production-server:7001",
    "username": "admin_user",
    "password": "admin_password"
  }
}
```

#### Option 3: Claude Desktop Configuration

Configure in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python",
      "args": ["/path/to/wlst-mcp/server.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://localhost:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password"
      }
    }
  }
}
```

### Parameter Priority Example

Given this configuration:

```bash
# Environment variables
export WLST_ADMIN_URL=t3://dev-server:7001
export WLST_USERNAME=dev_user
export WLST_PASSWORD=dev_password
```

And this tool call:

```json
{
  "tool": "wlst_list_servers",
  "params": {
    "admin_url": "t3://prod-server:7001"
  }
}
```

The resolved values will be:
| Parameter | Value | Source |
|-----------|-------|--------|
| `admin_url` | `t3://prod-server:7001` | Tool parameter (override) |
| `username` | `dev_user` | Environment variable (fallback) |
| `password` | `dev_password` | Environment variable (fallback) |

## Response Formats

Most tools support two output formats:

- **markdown**: Human-readable formatted output (default)
- **json**: Machine-readable JSON output for programmatic use

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
