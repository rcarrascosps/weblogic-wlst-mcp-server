# WLST MCP Server - Integration Guide

This guide explains how to integrate the WLST MCP Server with Claude Desktop and Claude Code.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Claude Code Integration](#claude-code-integration)
- [Environment Variables Reference](#environment-variables-reference)
- [Verifying the Integration](#verifying-the-integration)

---

## Prerequisites

Before integrating the MCP server, ensure you have:

1. **Python 3.8+** installed
2. **Oracle WebLogic Server** installed and running
3. **WLST** accessible (included with WebLogic)
4. **MCP dependencies** installed:

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes:
```
mcp>=1.0.0
pydantic>=2.0.0
```

---

## Claude Desktop Integration

### Step 1: Locate Configuration File

Find your Claude Desktop configuration file:

| OS | Configuration File Path |
|----|------------------------|
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

### Step 2: Configure the MCP Server

Add the WLST MCP server to your `claude_desktop_config.json`:

#### Windows Configuration

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python",
      "args": ["C:\\path\\to\\wlst-mcp-docs\\src\\wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://localhost:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password",
        "ORACLE_HOME": "C:\\Oracle\\Middleware\\Oracle_Home",
        "JAVA_HOME": "C:\\Program Files\\Java\\jdk-11"
      }
    }
  }
}
```

#### macOS/Linux Configuration

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python3",
      "args": ["/path/to/wlst-mcp-docs/src/wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://localhost:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password",
        "ORACLE_HOME": "/opt/oracle/middleware/oracle_home",
        "JAVA_HOME": "/usr/lib/jvm/java-11-openjdk"
      }
    }
  }
}
```

### Step 3: Restart Claude Desktop

After saving the configuration file, restart Claude Desktop for the changes to take effect.

### Step 4: Verify Integration

In Claude Desktop, you should now see the WLST MCP tools available. Try asking:

> "List the WebLogic servers"

or

> "Check the health of my WebLogic servers"

---

## Claude Code Integration

### Step 1: Locate Configuration File

Find your Claude Code MCP configuration file:

| OS | Configuration File Path |
|----|------------------------|
| **Windows** | `%APPDATA%\Claude\claude_code_config.json` |
| **macOS** | `~/Library/Application Support/Claude/claude_code_config.json` |
| **Linux** | `~/.config/Claude/claude_code_config.json` |

Alternatively, you can use the Claude Code CLI to manage MCP servers.

### Step 2: Configure via CLI (Recommended)

Use the Claude Code CLI to add the MCP server:

```bash
# Add the WLST MCP server
claude mcp add wlst-mcp

# When prompted, provide the configuration:
# Command: python (or python3 on Linux/macOS)
# Args: /path/to/wlst-mcp-docs/src/wlst_mcp.py
```

### Step 3: Configure via JSON File

Alternatively, edit the configuration file directly:

#### Windows

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python",
      "args": ["C:\\path\\to\\wlst-mcp-docs\\src\\wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://localhost:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password",
        "ORACLE_HOME": "C:\\Oracle\\Middleware\\Oracle_Home",
        "JAVA_HOME": "C:\\Program Files\\Java\\jdk-11",
        "WLST_PATH": "C:\\Oracle\\Middleware\\Oracle_Home\\oracle_common\\common\\bin\\wlst.cmd"
      }
    }
  }
}
```

#### macOS/Linux

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python3",
      "args": ["/path/to/wlst-mcp-docs/src/wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://localhost:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password",
        "ORACLE_HOME": "/opt/oracle/middleware/oracle_home",
        "JAVA_HOME": "/usr/lib/jvm/java-11-openjdk",
        "WLST_PATH": "/opt/oracle/middleware/oracle_home/oracle_common/common/bin/wlst.sh"
      }
    }
  }
}
```

### Step 4: Using with Virtual Environment

If you're using a Python virtual environment:

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\wlst-mcp-docs\\src\\wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://localhost:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password"
      }
    }
  }
}
```

---

## Environment Variables Reference

The WLST MCP Server uses the following environment variables:

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `WLST_ADMIN_URL` | WebLogic Admin Server URL | `t3://localhost:7001` |
| `WLST_USERNAME` | WebLogic admin username | `weblogic` |
| `WLST_PASSWORD` | WebLogic admin password | `welcome1` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ORACLE_HOME` | Oracle Middleware home directory | (none) |
| `JAVA_HOME` | JDK installation directory | (system default) |
| `WLST_PATH` | Full path to WLST executable | `wlst.cmd` (Windows) or `wlst.sh` (Linux/macOS) |
| `WEBLOGIC_HOME` | WebLogic installation home | (uses ORACLE_HOME if set) |
| `WLST_TIMEOUT` | Default timeout in seconds | `120` |

### How Variables Are Resolved

The MCP server resolves connection parameters in this order:

```
1. Tool parameter (if provided in the request)
      ↓
2. Environment variable (WLST_ADMIN_URL, etc.)
      ↓
3. Error (if required and not found)
```

This means you can:
- Set default values via environment variables
- Override them per-request using tool parameters

### WLST Path Resolution

The WLST executable path is resolved as follows:

1. If `WEBLOGIC_HOME` is set:
   - Windows: `%WEBLOGIC_HOME%\oracle_common\common\bin\wlst.cmd`
   - Linux/macOS: `$WEBLOGIC_HOME/oracle_common/common/bin/wlst.sh`

2. If `WLST_PATH` is set:
   - Uses the exact path specified

3. Otherwise:
   - Uses `wlst.cmd` (Windows) or `wlst.sh` (Linux/macOS) from system PATH

---

## Verifying the Integration

### Test 1: Check MCP Server is Running

In Claude Desktop or Claude Code, ask:

> "Test the WebLogic connection"

Expected response:
```
Connection successful!

- Domain: your_domain
- Version: 14.1.1.0.0
- URL: t3://localhost:7001
```

### Test 2: List Servers

Ask:

> "List all WebLogic servers"

Expected response:
```
# WebLogic Servers

**Total servers**: 2

- 🟢 **AdminServer**: RUNNING
- 🟢 **ManagedServer1**: RUNNING
```

### Test 3: Get Server Metrics

Ask:

> "Show me the JVM metrics for AdminServer"

### Troubleshooting

If the MCP server doesn't work:

1. **Check Python path**: Ensure the Python executable path is correct
2. **Check script path**: Verify the path to `wlst_mcp.py` is correct
3. **Check environment variables**: Ensure all required variables are set
4. **Check WLST access**: Verify WLST can connect to WebLogic manually
5. **Check logs**: Look for error messages in Claude Desktop/Code logs

#### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Module not found: mcp` | Missing dependencies | Run `pip install -r requirements.txt` |
| `WLST not found` | WLST_PATH not set | Set ORACLE_HOME or WLST_PATH |
| `Connection refused` | WebLogic not running | Start the Admin Server |
| `Authentication failed` | Wrong credentials | Check WLST_USERNAME and WLST_PASSWORD |

---

## Security Best Practices

### 1. Never Commit Credentials

Don't include passwords in version-controlled configuration files. Use environment variables or secure credential managers.

### 2. Use Secure Connections

For production, use SSL/TLS:

```json
{
  "env": {
    "WLST_ADMIN_URL": "t3s://weblogic-server:7002"
  }
}
```

### 3. Restrict Access

- Use dedicated admin accounts with minimal required permissions
- Consider using WebLogic's `Operator` role instead of `Admin`
- Enable audit logging in WebLogic

### 4. Protect Configuration Files

Ensure your configuration files have appropriate permissions:

```bash
# Linux/macOS
chmod 600 ~/.config/Claude/claude_desktop_config.json
```

---

## Example Configurations

### Development Environment

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python",
      "args": ["C:\\dev\\wlst-mcp\\src\\wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://localhost:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "welcome1",
        "WLST_TIMEOUT": "60"
      }
    }
  }
}
```

### Production Environment

```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python3",
      "args": ["/opt/tools/wlst-mcp/src/wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3s://weblogic-prod.example.com:7002",
        "WLST_USERNAME": "mcp_operator",
        "WLST_PASSWORD": "${WLST_PASSWORD}",
        "ORACLE_HOME": "/opt/oracle/middleware",
        "WLST_TIMEOUT": "300"
      }
    }
  }
}
```

### Multiple Environments

You can configure multiple MCP servers for different environments:

```json
{
  "mcpServers": {
    "wlst-dev": {
      "command": "python",
      "args": ["/path/to/wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3://dev-server:7001",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "dev_password"
      }
    },
    "wlst-prod": {
      "command": "python",
      "args": ["/path/to/wlst_mcp.py"],
      "env": {
        "WLST_ADMIN_URL": "t3s://prod-server:7002",
        "WLST_USERNAME": "prod_admin",
        "WLST_PASSWORD": "prod_password"
      }
    }
  }
}
```

Then specify which environment to use in your requests.

---

## Usage Examples

Once the MCP server is configured, you can interact with WebLogic using natural language. Below are practical examples for both Claude Desktop and Claude Code.

### Claude Desktop Examples

Claude Desktop provides a conversational interface. Simply type your requests:

#### Example 1: List Servers
```
You: List all my WebLogic servers

Claude: Here are your WebLogic servers:

# WebLogic Servers

**Total servers**: 2

- 🟢 **AdminServer**: RUNNING
- 🟢 **test_server1**: RUNNING
```

#### Example 2: Check Server Health
```
You: Check the health of test_server1

Claude: Here's the health status for test_server1:

## 🟢 test_server1
- **State**: RUNNING
- **Health**: HEALTH_OK
- **Open Sockets**: 6
- **Activation Time**: 1767462778307
```

#### Example 3: Get JVM Metrics
```
You: Show me the JVM metrics for test_server1

Claude: Here are the JVM metrics for test_server1:

## JVM Metrics
- **Heap Used**: 150.0 MB / 512.0 MB (29.3%)
- **Heap Free**: 70.7%
- **Uptime**: 3600 seconds
```

#### Example 4: Deploy an Application
```
You: Deploy the application myapp.war located at C:\apps\myapp.war to test_server1

Claude: Application **myapp** deployed successfully to test_server1.
```

#### Example 5: Execute Custom Script
```
You: Run a WLST script to get the domain name and version

Claude: I'll execute a custom WLST script for you:

Script executed successfully:

Domain Name: base_domain
Domain Version: 14.1.1.0.0
```

---

### Claude Code Examples

Claude Code is a CLI tool. You can interact with it directly from your terminal:

#### Example 1: Start a Server

```bash
$ claude

You: Start the server test_server1

Claude: I'll start the server test_server1 for you.

[Calling wlst_start_server with server_name: "test_server1"]

Server **test_server1** started successfully.
```

#### Example 2: Get Complete Metrics

```bash
$ claude

You: Give me all metrics for test_server1

Claude: I'll retrieve the complete metrics for test_server1.

[Calling wlst_execute_script]

# Metrics for test_server1

## Server State
- **State**: RUNNING
- **Health**: HEALTH_OK
- **Open Sockets**: 6

## JVM Metrics
- **Heap Current**: 256 MB
- **Heap Max**: 512 MB
- **Heap Free**: 106 MB (70%)
- **Uptime**: 886 seconds

## Thread Pool Metrics
- **Threads Total**: 13
- **Threads Idle**: 1
- **Hogging Threads**: 0
- **Pending Requests**: 0
```

#### Example 3: List Datasources

```bash
$ claude

You: Show me all JDBC datasources

Claude: I'll list all JDBC datasources in your domain.

[Calling wlst_list_datasources]

# JDBC Datasources

**Total**: 2

## MyAppDS
- **URL**: `jdbc:oracle:thin:@localhost:1521:ORCL`
- **Driver**: oracle.jdbc.OracleDriver
- **Targets**: test_server1, test_server2

## ReportingDS
- **URL**: `jdbc:oracle:thin:@dbserver:1521:REPORTS`
- **Driver**: oracle.jdbc.OracleDriver
- **Targets**: AdminServer
```

#### Example 4: Stop Server with Force Option

```bash
$ claude

You: Force stop the server test_server1

Claude: I'll force stop the server test_server1.

[Calling wlst_stop_server with server_name: "test_server1", force: true]

Server **test_server1** stopped successfully.
```

#### Example 5: Get Thread Dump for Debugging

```bash
$ claude

You: Get a thread dump from test_server1 for debugging

Claude: I'll capture a thread dump from test_server1.

[Calling wlst_thread_dump with server_name: "test_server1"]

# Thread Dump for test_server1

"ExecuteThread: '0' for queue: 'weblogic.kernel.Default'" daemon prio=5 tid=0x00007f...
   java.lang.Thread.State: WAITING
   at sun.misc.Unsafe.park(Native Method)
   ...
```

---

### Interactive Workflow Example

Here's a complete workflow example managing a WebLogic deployment:

```
You: I need to deploy a new version of my application. First, check the current status.

Claude: I'll check the current status of your servers and applications.

[Calling wlst_list_servers]
[Calling wlst_list_applications]

Current Status:
- AdminServer: 🟢 RUNNING
- test_server1: 🟢 RUNNING

Deployed Applications:
- myapp-v1.0: STATE_ACTIVE

You: Stop test_server1, undeploy myapp-v1.0, then deploy the new version from C:\releases\myapp-v2.0.war

Claude: I'll perform the deployment workflow:

1. Stopping test_server1...
   [Calling wlst_stop_server]
   ✓ Server stopped successfully.

2. Undeploying myapp-v1.0...
   [Calling wlst_undeploy]
   ✓ Application undeployed successfully.

3. Deploying myapp-v2.0...
   [Calling wlst_deploy]
   ✓ Application deployed successfully.

4. Starting test_server1...
   [Calling wlst_start_server]
   ✓ Server started successfully.

Deployment complete! The new version myapp-v2.0 is now active.

You: Verify everything is working

Claude: I'll verify the deployment.

[Calling wlst_server_health]
[Calling wlst_list_applications]

Verification Results:
- test_server1: 🟢 RUNNING, HEALTH_OK
- myapp-v2.0: STATE_ACTIVE

Everything looks good! ✓
```

---

### Tips for Effective Usage

| Tip | Description |
|-----|-------------|
| **Be specific** | Include server names and paths in your requests |
| **Use natural language** | "Start the server" works as well as technical commands |
| **Chain operations** | Ask for multiple operations in sequence |
| **Request verification** | Ask Claude to verify after making changes |
| **Use custom scripts** | For complex operations, ask for custom WLST scripts |
