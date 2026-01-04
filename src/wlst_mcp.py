#!/usr/bin/env python3
'''
MCP Server for Oracle WebLogic WLST (WebLogic Scripting Tool).

This server provides tools to interact with WebLogic Server domains including:
- Connection management (local/remote)
- Server administration (start, stop, status)
- Application deployment management
- Monitoring and health checks
- Configuration management (datasources, JMS)
- Custom WLST script execution
'''

import os
import json
import tempfile
import subprocess
import asyncio
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("wlst_mcp")

# =============================================================================
# Configuration
# =============================================================================

# WLST executable path - can be overridden via environment variable
WLST_PATH = os.environ.get("WLST_PATH", "wlst.cmd" if os.name == "nt" else "wlst.sh")
WEBLOGIC_HOME = os.environ.get("WEBLOGIC_HOME", "")
DEFAULT_TIMEOUT = int(os.environ.get("WLST_TIMEOUT", "120"))

# Default connection credentials from environment variables
DEFAULT_ADMIN_URL = os.environ.get("WLST_ADMIN_URL", "")
DEFAULT_USERNAME = os.environ.get("WLST_USERNAME", "")
DEFAULT_PASSWORD = os.environ.get("WLST_PASSWORD", "")

# =============================================================================
# Enums and Constants
# =============================================================================

class ResponseFormat(str, Enum):
    '''Output format for tool responses.'''
    MARKDOWN = "markdown"
    JSON = "json"

class ServerState(str, Enum):
    '''WebLogic Server states.'''
    RUNNING = "RUNNING"
    SHUTDOWN = "SHUTDOWN"
    STANDBY = "STANDBY"
    ADMIN = "ADMIN"
    STARTING = "STARTING"
    SUSPENDING = "SUSPENDING"
    FORCE_SUSPENDING = "FORCE_SUSPENDING"
    UNKNOWN = "UNKNOWN"

# =============================================================================
# Pydantic Models for Input Validation
# =============================================================================

class ConnectionInput(BaseModel):
    '''Input model for WebLogic connection.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(
        default=None,
        description="Admin Server URL (e.g., 't3://localhost:7001'). Uses WLST_ADMIN_URL env var if not provided.",
        max_length=500
    )
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.", max_length=100)
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    timeout: Optional[int] = Field(default=DEFAULT_TIMEOUT, description="Connection timeout in seconds", ge=10, le=600)

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

    @field_validator('admin_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not (v.startswith('t3://') or v.startswith('t3s://') or v.startswith('http://') or v.startswith('https://')):
            raise ValueError("URL must start with t3://, t3s://, http://, or https://")
        return v

class ListServersInput(BaseModel):
    '''Input model for listing servers.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class ServerOperationInput(BaseModel):
    '''Input model for server operations (start/stop/restart).'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    server_name: str = Field(..., description="Name of the managed server to operate on", min_length=1, max_length=100)
    force: Optional[bool] = Field(default=False, description="Force the operation (for stop/restart)")
    timeout: Optional[int] = Field(default=DEFAULT_TIMEOUT, description="Operation timeout in seconds", ge=10, le=600)

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class DeployInput(BaseModel):
    '''Input model for application deployment.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    app_name: str = Field(..., description="Application name", min_length=1, max_length=200)
    app_path: str = Field(..., description="Path to the application archive (WAR, EAR, JAR)")
    targets: Optional[str] = Field(default=None, description="Comma-separated list of target servers/clusters")
    stage_mode: Optional[str] = Field(default="stage", description="Deployment stage mode: stage, nostage, or external_stage")
    plan_path: Optional[str] = Field(default=None, description="Path to deployment plan XML")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

    @field_validator('stage_mode')
    @classmethod
    def validate_stage_mode(cls, v: str) -> str:
        valid_modes = ['stage', 'nostage', 'external_stage']
        if v.lower() not in valid_modes:
            raise ValueError(f"stage_mode must be one of: {', '.join(valid_modes)}")
        return v.lower()

class UndeployInput(BaseModel):
    '''Input model for application undeployment.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    app_name: str = Field(..., description="Name of the application to undeploy", min_length=1, max_length=200)
    targets: Optional[str] = Field(default=None, description="Comma-separated list of target servers/clusters (optional)")
    timeout: Optional[int] = Field(default=DEFAULT_TIMEOUT, description="Operation timeout", ge=10, le=600)

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class ListAppsInput(BaseModel):
    '''Input model for listing applications.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class ServerHealthInput(BaseModel):
    '''Input model for server health check.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    server_name: Optional[str] = Field(default=None, description="Specific server name (optional, all servers if not specified)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class ServerMetricsInput(BaseModel):
    '''Input model for server metrics.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    server_name: str = Field(..., description="Server name to get metrics for")
    metric_type: Optional[str] = Field(default="all", description="Type of metrics: all, jvm, threads, jdbc, jms")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

    @field_validator('metric_type')
    @classmethod
    def validate_metric_type(cls, v: str) -> str:
        valid_types = ['all', 'jvm', 'threads', 'jdbc', 'jms']
        if v.lower() not in valid_types:
            raise ValueError(f"metric_type must be one of: {', '.join(valid_types)}")
        return v.lower()

class DatasourceInput(BaseModel):
    '''Input model for datasource operations.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class CreateDatasourceInput(BaseModel):
    '''Input model for creating a datasource.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    ds_name: str = Field(..., description="Datasource name", min_length=1, max_length=200)
    jndi_name: str = Field(..., description="JNDI name (e.g., jdbc/myDS)", min_length=1, max_length=500)
    db_url: str = Field(..., description="Database JDBC URL")
    db_driver: str = Field(..., description="JDBC driver class name")
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
    targets: str = Field(..., description="Comma-separated list of target servers/clusters")
    min_capacity: Optional[int] = Field(default=1, description="Minimum pool capacity", ge=0, le=100)
    max_capacity: Optional[int] = Field(default=15, description="Maximum pool capacity", ge=1, le=500)

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class JMSInput(BaseModel):
    '''Input model for JMS operations.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class ExecuteScriptInput(BaseModel):
    '''Input model for executing custom WLST scripts.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided. Optional for offline scripts.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    script: str = Field(..., description="WLST/Jython script to execute", min_length=1)
    timeout: Optional[int] = Field(default=DEFAULT_TIMEOUT, description="Script execution timeout", ge=10, le=1800)

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

class ThreadDumpInput(BaseModel):
    '''Input model for thread dump.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    server_name: str = Field(..., description="Server name to get thread dump from")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

# =============================================================================
# Utility Functions
# =============================================================================

def _get_wlst_path() -> str:
    '''Get the full path to WLST executable.'''
    if WEBLOGIC_HOME:
        if os.name == "nt":
            return os.path.join(WEBLOGIC_HOME, "oracle_common", "common", "bin", "wlst.cmd")
        else:
            return os.path.join(WEBLOGIC_HOME, "oracle_common", "common", "bin", "wlst.sh")
    return WLST_PATH

async def _execute_wlst_script(script: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    '''Execute a WLST script and return the output.'''
    wlst_path = _get_wlst_path()

    # Create temporary script file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script)
        script_path = f.name

    try:
        # Execute WLST script
        process = await asyncio.create_subprocess_exec(
            wlst_path, script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, 'WLST_PROPERTIES': '-Dweblogic.security.SSL.ignoreHostnameVerification=true'}
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": f"Script execution timed out after {timeout} seconds",
                "stdout": "",
                "stderr": ""
            }

        stdout_str = stdout.decode('utf-8', errors='replace')
        stderr_str = stderr.decode('utf-8', errors='replace')

        return {
            "success": process.returncode == 0,
            "returncode": process.returncode,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "error": stderr_str if process.returncode != 0 else None
        }
    finally:
        # Clean up temporary file
        try:
            os.unlink(script_path)
        except:
            pass

def _build_connect_script(admin_url: str, username: str, password: str) -> str:
    '''Build WLST connect script fragment.'''
    return f'''
try:
    connect('{username}', '{password}', '{admin_url}')
except Exception as e:
    print('CONNECTION_ERROR: ' + str(e))
    exit(1)
'''

def _build_disconnect_script() -> str:
    '''Build WLST disconnect script fragment.'''
    return '''
try:
    disconnect()
except:
    pass
'''

def _handle_error(result: Dict[str, Any]) -> str:
    '''Handle WLST execution errors and return formatted message.'''
    if 'CONNECTION_ERROR' in result.get('stdout', ''):
        error_line = [l for l in result['stdout'].split('\n') if 'CONNECTION_ERROR' in l]
        return f"Error: Connection failed. {error_line[0] if error_line else 'Check credentials and URL.'}"
    if result.get('error'):
        return f"Error: {result['error']}"
    return "Error: Unknown error occurred during WLST execution"

def _parse_json_output(output: str) -> Optional[Dict]:
    '''Parse JSON output from WLST script.'''
    try:
        # Find JSON block in output
        lines = output.split('\n')
        json_lines = []
        in_json = False

        for line in lines:
            if line.strip().startswith('{') or line.strip().startswith('['):
                in_json = True
            if in_json:
                json_lines.append(line)
            if in_json and (line.strip().endswith('}') or line.strip().endswith(']')):
                break

        if json_lines:
            return json.loads('\n'.join(json_lines))
    except json.JSONDecodeError:
        pass
    return None

# =============================================================================
# Tool Implementations
# =============================================================================

@mcp.tool(
    name="wlst_test_connection",
    annotations={
        "title": "Test WebLogic Connection",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_test_connection(params: ConnectionInput) -> str:
    '''Test connection to a WebLogic Admin Server.

    This tool verifies connectivity to a WebLogic domain by attempting to connect
    to the Admin Server with the provided credentials.

    Args:
        params (ConnectionInput): Connection parameters including:
            - admin_url (str): Admin Server URL (e.g., 't3://localhost:7001')
            - username (str): WebLogic admin username
            - password (str): WebLogic admin password
            - timeout (Optional[int]): Connection timeout in seconds

    Returns:
        str: Success message with domain info or error message
    '''
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}
domainName = cmo.getName()
domainVersion = cmo.getDomainVersion()
print('CONNECTION_SUCCESS')
print('DOMAIN_NAME: ' + str(domainName))
print('DOMAIN_VERSION: ' + str(domainVersion))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'CONNECTION_SUCCESS' in result['stdout']:
        lines = result['stdout'].split('\n')
        domain_name = next((l.replace('DOMAIN_NAME: ', '') for l in lines if 'DOMAIN_NAME:' in l), 'Unknown')
        domain_version = next((l.replace('DOMAIN_VERSION: ', '') for l in lines if 'DOMAIN_VERSION:' in l), 'Unknown')
        return f"Connection successful!\n\n- **Domain**: {domain_name}\n- **Version**: {domain_version}\n- **URL**: {params.get_admin_url()}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_list_servers",
    annotations={
        "title": "List WebLogic Servers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_list_servers(params: ListServersInput) -> str:
    '''List all servers in a WebLogic domain with their status.

    Args:
        params (ListServersInput): Connection and format parameters

    Returns:
        str: List of servers in requested format (markdown or json)
    '''
    script = f'''
import json
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

servers = []
domainRuntime()
cd('ServerLifeCycleRuntimes')
serverNames = ls(returnMap='true')

for serverName in serverNames:
    cd(serverName)
    state = cmo.getState()
    servers.append({{'name': serverName, 'state': state}})
    cd('..')

print('SERVERS_JSON:' + json.dumps(servers))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script)

    if not result['success']:
        return _handle_error(result)

    # Parse servers from output
    servers = []
    for line in result['stdout'].split('\n'):
        if 'SERVERS_JSON:' in line:
            try:
                servers = json.loads(line.replace('SERVERS_JSON:', ''))
            except:
                pass

    if not servers:
        return "No servers found or unable to parse server list."

    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"servers": servers, "total": len(servers)}, indent=2)

    # Markdown format
    lines = ["# WebLogic Servers", "", f"**Total servers**: {len(servers)}", ""]
    for server in servers:
        state_emoji = "🟢" if server['state'] == 'RUNNING' else "🔴" if server['state'] == 'SHUTDOWN' else "🟡"
        lines.append(f"- {state_emoji} **{server['name']}**: {server['state']}")

    return '\n'.join(lines)

@mcp.tool(
    name="wlst_start_server",
    annotations={
        "title": "Start WebLogic Server",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wlst_start_server(params: ServerOperationInput) -> str:
    '''Start a managed server in a WebLogic domain.

    Args:
        params (ServerOperationInput): Server operation parameters

    Returns:
        str: Operation result message
    '''
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    start('{params.server_name}', 'Server')
    print('SERVER_STARTED: {params.server_name}')
except Exception as e:
    print('START_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'SERVER_STARTED' in result['stdout']:
        return f"Server **{params.server_name}** started successfully."

    if 'START_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'START_ERROR' in l]
        return f"Error starting server: {error_line[0].replace('START_ERROR: ', '') if error_line else 'Unknown error'}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_stop_server",
    annotations={
        "title": "Stop WebLogic Server",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wlst_stop_server(params: ServerOperationInput) -> str:
    '''Stop a managed server in a WebLogic domain.

    Args:
        params (ServerOperationInput): Server operation parameters including force option

    Returns:
        str: Operation result message
    '''
    force_param = ", force='true'" if params.force else ""
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    shutdown('{params.server_name}', 'Server'{force_param})
    print('SERVER_STOPPED: {params.server_name}')
except Exception as e:
    print('STOP_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'SERVER_STOPPED' in result['stdout']:
        return f"Server **{params.server_name}** stopped successfully."

    if 'STOP_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'STOP_ERROR' in l]
        return f"Error stopping server: {error_line[0].replace('STOP_ERROR: ', '') if error_line else 'Unknown error'}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_restart_server",
    annotations={
        "title": "Restart WebLogic Server",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wlst_restart_server(params: ServerOperationInput) -> str:
    '''Restart a managed server in a WebLogic domain.

    Args:
        params (ServerOperationInput): Server operation parameters

    Returns:
        str: Operation result message
    '''
    force_param = ", force='true'" if params.force else ""
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    shutdown('{params.server_name}', 'Server'{force_param})
    print('SERVER_STOPPED: {params.server_name}')
    start('{params.server_name}', 'Server')
    print('SERVER_RESTARTED: {params.server_name}')
except Exception as e:
    print('RESTART_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'SERVER_RESTARTED' in result['stdout']:
        return f"Server **{params.server_name}** restarted successfully."

    if 'RESTART_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'RESTART_ERROR' in l]
        return f"Error restarting server: {error_line[0].replace('RESTART_ERROR: ', '') if error_line else 'Unknown error'}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_deploy",
    annotations={
        "title": "Deploy Application",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wlst_deploy(params: DeployInput) -> str:
    '''Deploy an application to WebLogic Server.

    Args:
        params (DeployInput): Deployment parameters including app path, targets, and stage mode

    Returns:
        str: Deployment result message
    '''
    targets_param = f", targets='{params.targets}'" if params.targets else ""
    plan_param = f", planPath='{params.plan_path}'" if params.plan_path else ""

    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    deploy('{params.app_name}', '{params.app_path}'{targets_param}, stageMode='{params.stage_mode}'{plan_param})
    print('DEPLOY_SUCCESS: {params.app_name}')
except Exception as e:
    print('DEPLOY_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, DEFAULT_TIMEOUT * 2)  # Longer timeout for deployments

    if result['success'] and 'DEPLOY_SUCCESS' in result['stdout']:
        return f"Application **{params.app_name}** deployed successfully to {params.targets or 'default targets'}."

    if 'DEPLOY_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'DEPLOY_ERROR' in l]
        return f"Error deploying application: {error_line[0].replace('DEPLOY_ERROR: ', '') if error_line else 'Unknown error'}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_undeploy",
    annotations={
        "title": "Undeploy Application",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wlst_undeploy(params: UndeployInput) -> str:
    '''Undeploy an application from WebLogic Server.

    Args:
        params (UndeployInput): Undeployment parameters

    Returns:
        str: Undeployment result message
    '''
    targets_param = f", targets='{params.targets}'" if params.targets else ""

    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    undeploy('{params.app_name}'{targets_param})
    print('UNDEPLOY_SUCCESS: {params.app_name}')
except Exception as e:
    print('UNDEPLOY_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'UNDEPLOY_SUCCESS' in result['stdout']:
        return f"Application **{params.app_name}** undeployed successfully."

    if 'UNDEPLOY_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'UNDEPLOY_ERROR' in l]
        return f"Error undeploying application: {error_line[0].replace('UNDEPLOY_ERROR: ', '') if error_line else 'Unknown error'}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_list_applications",
    annotations={
        "title": "List Deployed Applications",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_list_applications(params: ListAppsInput) -> str:
    '''List all deployed applications in a WebLogic domain.

    Args:
        params (ListAppsInput): Connection and format parameters

    Returns:
        str: List of applications in requested format
    '''
    script = f'''
import json
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

apps = []
domainRuntime()
cd('AppRuntimeStateRuntime/AppRuntimeStateRuntime')
appNames = cmo.getApplicationIds()

for appName in appNames:
    state = cmo.getCurrentState(appName)
    intendedState = cmo.getIntendedState(appName)
    apps.append({{'name': appName, 'state': state, 'intendedState': intendedState}})

print('APPS_JSON:' + json.dumps(apps))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script)

    if not result['success']:
        return _handle_error(result)

    apps = []
    for line in result['stdout'].split('\n'):
        if 'APPS_JSON:' in line:
            try:
                apps = json.loads(line.replace('APPS_JSON:', ''))
            except:
                pass

    if not apps:
        return "No applications deployed or unable to parse application list."

    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"applications": apps, "total": len(apps)}, indent=2)

    lines = ["# Deployed Applications", "", f"**Total applications**: {len(apps)}", ""]
    for app in apps:
        state_emoji = "🟢" if app['state'] == 'STATE_ACTIVE' else "🔴"
        lines.append(f"- {state_emoji} **{app['name']}**")
        lines.append(f"  - State: {app['state']}")
        lines.append(f"  - Intended: {app['intendedState']}")

    return '\n'.join(lines)

@mcp.tool(
    name="wlst_server_health",
    annotations={
        "title": "Server Health Check",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_server_health(params: ServerHealthInput) -> str:
    '''Get health status of WebLogic servers.

    Args:
        params (ServerHealthInput): Health check parameters

    Returns:
        str: Health status in requested format
    '''
    server_filter = f"if serverName == '{params.server_name}':" if params.server_name else "if True:"

    script = f'''
import json
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

health_data = []
domainRuntime()
cd('ServerRuntimes')
servers = ls(returnMap='true')

for serverName in servers:
    {server_filter}
        cd(serverName)
        state = cmo.getState()
        health = cmo.getHealthState()

        server_health = {{
            'name': serverName,
            'state': state,
            'health': str(health),
            'openSocketsCurrentCount': cmo.getOpenSocketsCurrentCount(),
            'activationTime': str(cmo.getActivationTime()) if cmo.getActivationTime() else None
        }}
        health_data.append(server_health)
        cd('..')

print('HEALTH_JSON:' + json.dumps(health_data))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script)

    if not result['success']:
        return _handle_error(result)

    health_data = []
    for line in result['stdout'].split('\n'):
        if 'HEALTH_JSON:' in line:
            try:
                health_data = json.loads(line.replace('HEALTH_JSON:', ''))
            except:
                pass

    if not health_data:
        return "No health data available or unable to parse."

    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"servers": health_data}, indent=2)

    lines = ["# Server Health Status", ""]
    for server in health_data:
        health_emoji = "🟢" if "HEALTH_OK" in server.get('health', '') else "🔴"
        lines.append(f"## {health_emoji} {server['name']}")
        lines.append(f"- **State**: {server['state']}")
        lines.append(f"- **Health**: {server['health']}")
        lines.append(f"- **Open Sockets**: {server.get('openSocketsCurrentCount', 'N/A')}")
        if server.get('activationTime'):
            lines.append(f"- **Activation Time**: {server['activationTime']}")
        lines.append("")

    return '\n'.join(lines)

@mcp.tool(
    name="wlst_server_metrics",
    annotations={
        "title": "Server Metrics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_server_metrics(params: ServerMetricsInput) -> str:
    '''Get detailed metrics for a WebLogic server (JVM, threads, JDBC, JMS).

    Args:
        params (ServerMetricsInput): Metrics parameters including metric type

    Returns:
        str: Server metrics in requested format
    '''
    script = f'''
import json
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

metrics = {{'server': '{params.server_name}'}}

try:
    domainRuntime()
    serverPath = 'ServerRuntimes/{params.server_name}'

    # JVM metrics
    if '{params.metric_type}' in ['all', 'jvm']:
        try:
            cd(serverPath + '/JVMRuntime/{params.server_name}')
            metrics['jvm'] = {{
                'heapSizeCurrent': cmo.getHeapSizeCurrent(),
                'heapSizeMax': cmo.getHeapSizeMax(),
                'heapFreeCurrent': cmo.getHeapFreeCurrent(),
                'heapFreePercent': cmo.getHeapFreePercent(),
                'uptime': cmo.getUptime()
            }}
        except Exception as jvmEx:
            metrics['jvm'] = {{'error': str(jvmEx)}}

    # Thread metrics
    if '{params.metric_type}' in ['all', 'threads']:
        try:
            cd(serverPath + '/ThreadPoolRuntime/ThreadPoolRuntime')
            metrics['threads'] = {{
                'executeThreadTotalCount': cmo.getExecuteThreadTotalCount(),
                'executeThreadIdleCount': cmo.getExecuteThreadIdleCount(),
                'hoggingThreadCount': cmo.getHoggingThreadCount(),
                'pendingUserRequestCount': cmo.getPendingUserRequestCount(),
                'queueLength': cmo.getQueueLength()
            }}
        except Exception as threadEx:
            metrics['threads'] = {{'error': str(threadEx)}}

    # JDBC metrics
    if '{params.metric_type}' in ['all', 'jdbc']:
        try:
            cd(serverPath + '/JDBCServiceRuntime/{params.server_name}')
            dsRuntimes = ls('JDBCDataSourceRuntimeMBeans', returnMap='true')
            jdbc_data = []
            if dsRuntimes:
                for dsName in dsRuntimes:
                    cd('JDBCDataSourceRuntimeMBeans/' + dsName)
                    jdbc_data.append({{
                        'name': dsName,
                        'state': cmo.getState(),
                        'activeConnectionsCurrentCount': cmo.getActiveConnectionsCurrentCount(),
                        'activeConnectionsHighCount': cmo.getActiveConnectionsHighCount(),
                        'connectionsTotalCount': cmo.getConnectionsTotalCount(),
                        'waitingForConnectionCurrentCount': cmo.getWaitingForConnectionCurrentCount()
                    }})
                    cd('..')
            metrics['jdbc'] = jdbc_data
        except Exception as jdbcEx:
            metrics['jdbc'] = {{'error': str(jdbcEx)}}

    print('METRICS_JSON:' + json.dumps(metrics))
except Exception as e:
    print('METRICS_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script)

    if not result['success']:
        return _handle_error(result)

    metrics = None
    for line in result['stdout'].split('\n'):
        if 'METRICS_JSON:' in line:
            try:
                metrics = json.loads(line.replace('METRICS_JSON:', ''))
            except:
                pass

    if not metrics:
        if 'METRICS_ERROR' in result['stdout']:
            error_line = [l for l in result['stdout'].split('\n') if 'METRICS_ERROR' in l]
            return f"Error getting metrics: {error_line[0].replace('METRICS_ERROR: ', '') if error_line else 'Unknown error'}"
        return "Unable to retrieve metrics."

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(metrics, indent=2)

    lines = [f"# Metrics for {params.server_name}", ""]

    if 'jvm' in metrics:
        jvm = metrics['jvm']
        if 'error' in jvm:
            lines.extend([
                "## JVM Metrics",
                f"- **Error**: {jvm['error']}",
                ""
            ])
        else:
            heap_used = jvm['heapSizeCurrent'] - jvm['heapFreeCurrent']
            heap_used_mb = heap_used / (1024 * 1024)
            heap_max_mb = jvm['heapSizeMax'] / (1024 * 1024)
            lines.extend([
                "## JVM Metrics",
                f"- **Heap Used**: {heap_used_mb:.1f} MB / {heap_max_mb:.1f} MB ({100 - jvm['heapFreePercent']:.1f}%)",
                f"- **Heap Free**: {jvm['heapFreePercent']:.1f}%",
                f"- **Uptime**: {jvm['uptime'] / 1000:.0f} seconds",
                ""
            ])

    if 'threads' in metrics:
        t = metrics['threads']
        if 'error' in t:
            lines.extend([
                "## Thread Pool Metrics",
                f"- **Error**: {t['error']}",
                ""
            ])
        else:
            lines.extend([
                "## Thread Pool Metrics",
                f"- **Total Threads**: {t['executeThreadTotalCount']}",
                f"- **Idle Threads**: {t['executeThreadIdleCount']}",
                f"- **Hogging Threads**: {t['hoggingThreadCount']}",
                f"- **Pending Requests**: {t['pendingUserRequestCount']}",
                f"- **Queue Length**: {t['queueLength']}",
                ""
            ])

    if 'jdbc' in metrics and metrics['jdbc']:
        jdbc = metrics['jdbc']
        if isinstance(jdbc, dict) and 'error' in jdbc:
            lines.extend([
                "## JDBC Datasource Metrics",
                f"- **Error**: {jdbc['error']}",
                ""
            ])
        elif isinstance(jdbc, list):
            lines.append("## JDBC Datasource Metrics")
            for ds in jdbc:
                lines.extend([
                    f"### {ds['name']}",
                    f"- **State**: {ds['state']}",
                    f"- **Active Connections**: {ds['activeConnectionsCurrentCount']} (High: {ds['activeConnectionsHighCount']})",
                    f"- **Total Connections**: {ds['connectionsTotalCount']}",
                    f"- **Waiting for Connection**: {ds['waitingForConnectionCurrentCount']}",
                    ""
                ])

    return '\n'.join(lines)

@mcp.tool(
    name="wlst_list_datasources",
    annotations={
        "title": "List Datasources",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_list_datasources(params: DatasourceInput) -> str:
    '''List all JDBC datasources in a WebLogic domain.

    Args:
        params (DatasourceInput): Connection and format parameters

    Returns:
        str: List of datasources in requested format
    '''
    script = f'''
import json
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

datasources = []
serverConfig()
cd('JDBCSystemResources')
dsNames = ls(returnMap='true')

for dsName in dsNames:
    cd(dsName + '/JDBCResource/' + dsName + '/JDBCDriverParams/' + dsName)
    url = cmo.getUrl()
    driverName = cmo.getDriverName()
    cd('../../../../..')

    cd(dsName)
    targets = cmo.getTargets()
    targetNames = [t.getName() for t in targets] if targets else []
    cd('..')

    datasources.append({{
        'name': dsName,
        'url': url,
        'driver': driverName,
        'targets': targetNames
    }})

print('DS_JSON:' + json.dumps(datasources))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script)

    if not result['success']:
        return _handle_error(result)

    datasources = []
    for line in result['stdout'].split('\n'):
        if 'DS_JSON:' in line:
            try:
                datasources = json.loads(line.replace('DS_JSON:', ''))
            except:
                pass

    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"datasources": datasources, "total": len(datasources)}, indent=2)

    lines = ["# JDBC Datasources", "", f"**Total**: {len(datasources)}", ""]
    for ds in datasources:
        lines.extend([
            f"## {ds['name']}",
            f"- **URL**: `{ds['url']}`",
            f"- **Driver**: {ds['driver']}",
            f"- **Targets**: {', '.join(ds['targets']) if ds['targets'] else 'None'}",
            ""
        ])

    return '\n'.join(lines)

@mcp.tool(
    name="wlst_list_jms_resources",
    annotations={
        "title": "List JMS Resources",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_list_jms_resources(params: JMSInput) -> str:
    '''List all JMS resources (servers, modules, queues, topics) in a WebLogic domain.

    Args:
        params (JMSInput): Connection and format parameters

    Returns:
        str: List of JMS resources in requested format
    '''
    script = f'''
import json
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

jms_data = {{'servers': [], 'modules': []}}

serverConfig()

# JMS Servers
cd('JMSServers')
jmsServers = ls(returnMap='true')
for serverName in jmsServers:
    cd(serverName)
    targets = cmo.getTargets()
    targetNames = [t.getName() for t in targets] if targets else []
    jms_data['servers'].append({{'name': serverName, 'targets': targetNames}})
    cd('..')

cd('..')

# JMS Modules
cd('JMSSystemResources')
modules = ls(returnMap='true')
for moduleName in modules:
    module_data = {{'name': moduleName, 'queues': [], 'topics': []}}
    cd(moduleName + '/JMSResource/' + moduleName)

    # Queues
    try:
        cd('Queues')
        queues = ls(returnMap='true')
        for queueName in queues:
            cd(queueName)
            jndiName = cmo.getJNDIName()
            module_data['queues'].append({{'name': queueName, 'jndiName': jndiName}})
            cd('..')
        cd('..')
    except:
        pass

    # Topics
    try:
        cd('Topics')
        topics = ls(returnMap='true')
        for topicName in topics:
            cd(topicName)
            jndiName = cmo.getJNDIName()
            module_data['topics'].append({{'name': topicName, 'jndiName': jndiName}})
            cd('..')
        cd('..')
    except:
        pass

    jms_data['modules'].append(module_data)
    cd('../../..')

print('JMS_JSON:' + json.dumps(jms_data))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script)

    if not result['success']:
        return _handle_error(result)

    jms_data = {'servers': [], 'modules': []}
    for line in result['stdout'].split('\n'):
        if 'JMS_JSON:' in line:
            try:
                jms_data = json.loads(line.replace('JMS_JSON:', ''))
            except:
                pass

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(jms_data, indent=2)

    lines = ["# JMS Resources", ""]

    lines.append("## JMS Servers")
    if jms_data['servers']:
        for server in jms_data['servers']:
            lines.append(f"- **{server['name']}** → {', '.join(server['targets']) if server['targets'] else 'No targets'}")
    else:
        lines.append("- No JMS servers configured")
    lines.append("")

    lines.append("## JMS Modules")
    for module in jms_data['modules']:
        lines.append(f"### {module['name']}")
        if module['queues']:
            lines.append("**Queues:**")
            for q in module['queues']:
                lines.append(f"- {q['name']} (`{q['jndiName']}`)")
        if module['topics']:
            lines.append("**Topics:**")
            for t in module['topics']:
                lines.append(f"- {t['name']} (`{t['jndiName']}`)")
        if not module['queues'] and not module['topics']:
            lines.append("- No queues or topics")
        lines.append("")

    return '\n'.join(lines)

@mcp.tool(
    name="wlst_thread_dump",
    annotations={
        "title": "Get Thread Dump",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_thread_dump(params: ThreadDumpInput) -> str:
    '''Get a thread dump from a WebLogic server for debugging.

    Args:
        params (ThreadDumpInput): Thread dump parameters

    Returns:
        str: Thread dump output
    '''
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    serverRuntime()
    cd('/ServerRuntimes/{params.server_name}')
    threadDump = cmo.getThreadStackDump()
    print('THREAD_DUMP_START')
    print(threadDump)
    print('THREAD_DUMP_END')
except Exception as e:
    print('THREAD_DUMP_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script)

    if not result['success']:
        return _handle_error(result)

    if 'THREAD_DUMP_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'THREAD_DUMP_ERROR' in l]
        return f"Error getting thread dump: {error_line[0].replace('THREAD_DUMP_ERROR: ', '') if error_line else 'Unknown error'}"

    # Extract thread dump
    output = result['stdout']
    start_idx = output.find('THREAD_DUMP_START')
    end_idx = output.find('THREAD_DUMP_END')

    if start_idx != -1 and end_idx != -1:
        thread_dump = output[start_idx + len('THREAD_DUMP_START'):end_idx].strip()
        return f"# Thread Dump for {params.server_name}\n\n```\n{thread_dump}\n```"

    return "Unable to retrieve thread dump."

@mcp.tool(
    name="wlst_execute_script",
    annotations={
        "title": "Execute Custom WLST Script",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wlst_execute_script(params: ExecuteScriptInput) -> str:
    '''Execute a custom WLST/Jython script.

    This tool allows running arbitrary WLST commands. Use with caution as it can
    modify server configuration. The script can optionally connect to a server
    if credentials are provided.

    Args:
        params (ExecuteScriptInput): Script execution parameters including:
            - script (str): The WLST/Jython script to execute
            - admin_url (Optional[str]): Admin URL for online operations
            - username (Optional[str]): Admin username
            - password (Optional[str]): Admin password
            - timeout (Optional[int]): Execution timeout

    Returns:
        str: Script execution output
    '''
    # Build the full script
    admin_url = params.get_admin_url()
    username = params.get_username()
    password = params.get_password()
    if admin_url and username and password:
        full_script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

# User script starts here
{params.script}
# User script ends here

{_build_disconnect_script()}
'''
    else:
        full_script = params.script

    result = await _execute_wlst_script(full_script, params.timeout or DEFAULT_TIMEOUT)

    if not result['success']:
        return f"Script execution failed:\n\n**STDOUT:**\n```\n{result['stdout']}\n```\n\n**STDERR:**\n```\n{result['stderr']}\n```"

    return f"Script executed successfully:\n\n```\n{result['stdout']}\n```"


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
