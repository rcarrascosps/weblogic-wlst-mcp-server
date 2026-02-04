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
DEFAULT_SHUTDOWN_TIMEOUT = int(os.environ.get("WLST_SHUTDOWN_TIMEOUT", "300"))

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
    force: Optional[bool] = Field(default=False, description="Force shutdown (immediate). If false, graceful shutdown waits for sessions to complete.")
    timeout: Optional[int] = Field(default=DEFAULT_SHUTDOWN_TIMEOUT, description="Operation timeout in seconds. Graceful shutdown may need longer timeout.", ge=10, le=600)

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

class AppOperationInput(BaseModel):
    '''Input model for application operations (start/stop/redeploy).'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    app_name: str = Field(..., description="Name of the application", min_length=1, max_length=200)
    timeout: Optional[int] = Field(default=DEFAULT_TIMEOUT, description="Operation timeout in seconds", ge=10, le=600)

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

class ServerLogsInput(BaseModel):
    '''Input model for analyzing server logs via NodeManager.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    server_name: str = Field(..., description="Name of the server to analyze logs for", min_length=1, max_length=100)
    days: Optional[int] = Field(default=1, description="Number of days to analyze (how far back in time). Default is 1 day.", ge=1, le=30)
    log_type: Optional[str] = Field(default="all", description="Type of logs to analyze: all, server, nodemanager, stdout")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    def get_admin_url(self) -> str:
        return self.admin_url or DEFAULT_ADMIN_URL

    def get_username(self) -> str:
        return self.username or DEFAULT_USERNAME

    def get_password(self) -> str:
        return self.password or DEFAULT_PASSWORD

    def get_days(self) -> int:
        return self.days or 1

    @field_validator('log_type')
    @classmethod
    def validate_log_type(cls, v: str) -> str:
        valid_types = ['all', 'server', 'nodemanager', 'stdout']
        if v.lower() not in valid_types:
            raise ValueError(f"log_type must be one of: {', '.join(valid_types)}")
        return v.lower()

class AppDiagnosticInput(BaseModel):
    '''Input model for application diagnostics.'''
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    admin_url: Optional[str] = Field(default=None, description="Admin Server URL. Uses WLST_ADMIN_URL env var if not provided.")
    username: Optional[str] = Field(default=None, description="WebLogic admin username. Uses WLST_USERNAME env var if not provided.")
    password: Optional[str] = Field(default=None, description="WebLogic admin password. Uses WLST_PASSWORD env var if not provided.")
    app_name: Optional[str] = Field(
        default=None,
        description="Application name to diagnose. If not provided, diagnoses all applications in FAILED state.",
        max_length=200
    )
    check_logs: Optional[bool] = Field(
        default=True,
        description="Search server logs for related errors (may take longer)"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

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
serverNamesRaw = ls(returnMap='true')

# Handle both dict and list types returned by ls()
if serverNamesRaw:
    if hasattr(serverNamesRaw, 'keys'):
        serverNames = list(serverNamesRaw.keys())
    else:
        serverNames = list(serverNamesRaw)
else:
    serverNames = []

for i in range(len(serverNames)):
    name = str(serverNames[i])
    try:
        cd('/ServerLifeCycleRuntimes/' + name)
        state = str(cmo.getState())
        servers.append({{'name': name, 'state': state}})
    except Exception as e:
        servers.append({{'name': name, 'state': 'ERROR: ' + str(e)}})

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
    domainRuntime()
    cd('ServerLifeCycleRuntimes/{params.server_name}')
    serverState = cmo.getState()
    print('SERVER_STATE: ' + serverState)

    if serverState == 'SHUTDOWN':
        print('SERVER_ALREADY_STOPPED: {params.server_name}')
    elif serverState in ['RUNNING', 'ADMIN', 'RESUMING']:
        shutdown('{params.server_name}', 'Server', ignoreSessions='true', timeOut=90{force_param})
        print('SERVER_STOPPED: {params.server_name}')
    elif serverState in ['STARTING', 'STANDBY', 'SUSPENDING']:
        shutdown('{params.server_name}', 'Server', ignoreSessions='true', timeOut=90, force='true')
        print('SERVER_STOPPED: {params.server_name}')
    else:
        print('SERVER_UNKNOWN_STATE: ' + serverState)
except Exception as e:
    print('STOP_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_SHUTDOWN_TIMEOUT)

    if result['success'] and 'SERVER_STOPPED' in result['stdout']:
        return f"Server **{params.server_name}** stopped successfully."

    if 'SERVER_ALREADY_STOPPED' in result['stdout']:
        return f"Server **{params.server_name}** is already stopped."

    if 'SERVER_UNKNOWN_STATE' in result['stdout']:
        state_line = [l for l in result['stdout'].split('\n') if 'SERVER_STATE' in l]
        state = state_line[0].replace('SERVER_STATE: ', '') if state_line else 'unknown'
        return f"Server **{params.server_name}** is in state **{state}** and cannot be stopped normally."

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
    shutdown('{params.server_name}', 'Server', ignoreSessions='true', timeOut=120{force_param})
    print('SERVER_STOPPED: {params.server_name}')
    start('{params.server_name}', 'Server')
    print('SERVER_RESTARTED: {params.server_name}')
except Exception as e:
    print('RESTART_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_SHUTDOWN_TIMEOUT)

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
    plan_param = f", planPath='{params.plan_path.replace(chr(92), '/')}'" if params.plan_path else ""
    # Convert backslashes to forward slashes for Windows path compatibility
    app_path_safe = params.app_path.replace('\\', '/')

    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    deploy('{params.app_name}', '{app_path_safe}'{targets_param}, stageMode='{params.stage_mode}'{plan_param})
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
    name="wlst_start_application",
    annotations={
        "title": "Start Application",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_start_application(params: AppOperationInput) -> str:
    '''Start a deployed application in WebLogic Server.

    Args:
        params (AppOperationInput): Application operation parameters

    Returns:
        str: Operation result message
    '''
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    startApplication('{params.app_name}')
    print('START_SUCCESS: {params.app_name}')
except Exception as e:
    print('START_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'START_SUCCESS' in result['stdout']:
        return f"Application **{params.app_name}** started successfully."

    if 'START_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'START_ERROR' in l]
        return f"Error starting application: {error_line[0].replace('START_ERROR: ', '') if error_line else 'Unknown error'}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_stop_application",
    annotations={
        "title": "Stop Application",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_stop_application(params: AppOperationInput) -> str:
    '''Stop a running application in WebLogic Server (without undeploying).

    Args:
        params (AppOperationInput): Application operation parameters

    Returns:
        str: Operation result message
    '''
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    stopApplication('{params.app_name}')
    print('STOP_SUCCESS: {params.app_name}')
except Exception as e:
    print('STOP_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'STOP_SUCCESS' in result['stdout']:
        return f"Application **{params.app_name}** stopped successfully."

    if 'STOP_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'STOP_ERROR' in l]
        return f"Error stopping application: {error_line[0].replace('STOP_ERROR: ', '') if error_line else 'Unknown error'}"

    return _handle_error(result)

@mcp.tool(
    name="wlst_redeploy_application",
    annotations={
        "title": "Redeploy Application",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wlst_redeploy_application(params: AppOperationInput) -> str:
    '''Redeploy an application in WebLogic Server (updates the application in place).

    Args:
        params (AppOperationInput): Application operation parameters

    Returns:
        str: Operation result message
    '''
    script = f'''
{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

try:
    redeploy('{params.app_name}')
    print('REDEPLOY_SUCCESS: {params.app_name}')
except Exception as e:
    print('REDEPLOY_ERROR: ' + str(e))

{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, params.timeout or DEFAULT_TIMEOUT)

    if result['success'] and 'REDEPLOY_SUCCESS' in result['stdout']:
        return f"Application **{params.app_name}** redeployed successfully."

    if 'REDEPLOY_ERROR' in result['stdout']:
        error_line = [l for l in result['stdout'].split('\n') if 'REDEPLOY_ERROR' in l]
        return f"Error redeploying application: {error_line[0].replace('REDEPLOY_ERROR: ', '') if error_line else 'Unknown error'}"

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

# Get targets from serverConfig
serverConfig()
cd('AppDeployments')
appDeploymentsRaw = ls(returnMap='true')
appDeploymentsList = list(appDeploymentsRaw) if appDeploymentsRaw else []

appTargetsMap = {{}}
appInfoMap = {{}}

for i in range(len(appDeploymentsList)):
    appName = str(appDeploymentsList[i])

    # Get targets
    cd(appName + '/Targets')
    targetsRaw = ls(returnMap='true')
    if targetsRaw:
        appTargetsMap[appName] = [str(t) for t in list(targetsRaw)]
    else:
        appTargetsMap[appName] = []
    cd('../..')

    # Get module type and source path
    cd(appName)
    appInfoMap[appName] = {{
        'moduleType': str(cmo.getModuleType()) if cmo.getModuleType() else 'unknown',
        'sourcePath': str(cmo.getSourcePath()) if cmo.getSourcePath() else ''
    }}
    cd('..')

# Get runtime state from domainRuntime
domainRuntime()
cd('AppRuntimeStateRuntime/AppRuntimeStateRuntime')
appNamesRaw = cmo.getApplicationIds()
appNamesList = list(appNamesRaw) if appNamesRaw else []

for i in range(len(appNamesList)):
    appName = str(appNamesList[i])
    targetStates = []
    targets = appTargetsMap.get(appName, [])

    for j in range(len(targets)):
        targetName = str(targets[j])
        try:
            state = cmo.getCurrentState(appName, targetName)
            targetStates.append({{'target': targetName, 'state': str(state) if state else 'None'}})
        except:
            targetStates.append({{'target': targetName, 'state': 'UNKNOWN'}})

    intendedState = str(cmo.getIntendedState(appName))
    appInfo = appInfoMap.get(appName, {{}})
    apps.append({{
        'name': appName,
        'moduleType': appInfo.get('moduleType', 'unknown'),
        'sourcePath': appInfo.get('sourcePath', ''),
        'targets': targetStates,
        'intendedState': intendedState
    }})

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
        # Get the actual runtime state from targets (getCurrentState), not intendedState
        targets = app.get('targets', [])
        target_states = [t.get('state', 'UNKNOWN') for t in targets]

        # Determine overall app state based on target states
        # If any target shows FAILED, the app is failed
        # If all targets show STATE_ACTIVE, the app is active
        has_failed = any('FAILED' in s.upper() for s in target_states)
        has_active = any('STATE_ACTIVE' in s for s in target_states)
        has_prepared = any('STATE_PREPARED' in s for s in target_states)

        if has_failed:
            app_emoji = "🔴"
            overall_state = "STATE_FAILED"
        elif has_active and not has_prepared:
            app_emoji = "🟢"
            overall_state = "STATE_ACTIVE"
        elif has_prepared:
            app_emoji = "🟡"
            overall_state = "STATE_PREPARED"
        else:
            app_emoji = "🟡"
            overall_state = target_states[0] if target_states else "UNKNOWN"

        lines.append(f"## {app_emoji} **{app['name']}**")
        lines.append(f"- **Type**: {app.get('moduleType', 'unknown')}")
        lines.append(f"- **State**: {overall_state}")

        # Show per-target state if there are multiple targets or if state differs from intended
        intended = app.get('intendedState', 'UNKNOWN')
        if len(targets) > 1 or overall_state != intended:
            for t in targets:
                target_emoji = "🟢" if t.get('state') == 'STATE_ACTIVE' else "🔴" if 'FAILED' in t.get('state', '').upper() else "🟡"
                lines.append(f"  - {target_emoji} {t['target']}: {t.get('state', 'UNKNOWN')}")
            if overall_state != intended:
                lines.append(f"- **Intended State**: {intended}")
        else:
            lines.append(f"- **Targets**: {', '.join([t['target'] for t in targets])}")
        lines.append("")

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

@mcp.tool(
    name="wlst_analyze_logs",
    annotations={
        "title": "Analyze Server Logs via NodeManager",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_analyze_logs(params: ServerLogsInput) -> str:
    '''Analyze WebLogic server logs to identify restart reasons, errors, and issues.

    This tool connects to the Admin Server and retrieves log information for a
    specified managed server, analyzing logs from the NodeManager and server
    output to identify restart events, OutOfMemoryErrors, JVM crashes, and
    other critical issues.

    Args:
        params (ServerLogsInput): Log analysis parameters including:
            - server_name (str): Name of the server to analyze
            - days (int): How many days back to analyze (default: 1, max: 30)
            - log_type (str): Type of logs: all, server, nodemanager, stdout
            - response_format: Output format (markdown or json)

    Returns:
        str: Analysis results with identified issues and restart reasons
    '''
    days_to_analyze = params.get_days()

    script = f'''
import json
import os
import re
from datetime import datetime, timedelta
from java.util import Date
from java.text import SimpleDateFormat

{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

analysis = {{
    'server_name': '{params.server_name}',
    'days_analyzed': {days_to_analyze},
    'log_type': '{params.log_type}',
    'server_info': {{}},
    'restart_events': [],
    'errors': [],
    'warnings': [],
    'nodemanager_events': [],
    'summary': {{}}
}}

# Get domain home path
serverConfig()
domainHome = cmo.getRootDirectory()
analysis['domain_home'] = str(domainHome)

# Get server configuration
try:
    cd('/Servers/{params.server_name}')
    analysis['server_info']['listen_port'] = cmo.getListenPort()
    analysis['server_info']['listen_address'] = str(cmo.getListenAddress()) if cmo.getListenAddress() else 'localhost'
    analysis['server_info']['auto_restart'] = cmo.getAutoRestart()
    analysis['server_info']['restart_max'] = cmo.getRestartMax()
    analysis['server_info']['restart_interval_seconds'] = cmo.getRestartIntervalSeconds()
    machine = cmo.getMachine()
    if machine:
        analysis['server_info']['machine'] = machine.getName()
except Exception as e:
    analysis['server_info']['error'] = str(e)

# Get current server state and NodeManager restart count
try:
    domainRuntime()
    cd('/ServerLifeCycleRuntimes/{params.server_name}')
    analysis['server_info']['current_state'] = str(cmo.getState())
    analysis['server_info']['nm_restart_count'] = cmo.getNodeManagerRestartCount()
except Exception as e:
    analysis['server_info']['state_error'] = str(e)

# Calculate time threshold
cutoff_time = datetime.now() - timedelta(days={days_to_analyze})
cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
analysis['time_range'] = {{'from': cutoff_str, 'to': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}

# Define log file paths
server_log_dir = os.path.join(str(domainHome), 'servers', '{params.server_name}', 'logs')
nm_log_path = os.path.join(str(domainHome), 'nodemanager', 'nodemanager.log')

# Patterns to search for
restart_patterns = [
    (r'Starting.*{params.server_name}', 'SERVER_START'),
    (r'Stopping.*{params.server_name}', 'SERVER_STOP'),
    (r'Server.*{params.server_name}.*started', 'SERVER_STARTED'),
    (r'Server.*{params.server_name}.*stopped', 'SERVER_STOPPED'),
    (r'Server.*{params.server_name}.*failed', 'SERVER_FAILED'),
    (r'Auto restart', 'AUTO_RESTART'),
    (r'NodeManager.*restart', 'NM_RESTART'),
    (r'Process.*crashed', 'PROCESS_CRASH'),
    (r'Process.*exited', 'PROCESS_EXIT'),
]

error_patterns = [
    (r'OutOfMemoryError', 'OUT_OF_MEMORY'),
    (r'StackOverflowError', 'STACK_OVERFLOW'),
    (r'java\\.lang\\.Error', 'JAVA_ERROR'),
    (r'SIGSEGV|SIGKILL|SIGABRT', 'JVM_CRASH'),
    (r'BEA-\\d+.*Error', 'WEBLOGIC_ERROR'),
    (r'Exception.*fatal', 'FATAL_EXCEPTION'),
    (r'Connection refused', 'CONNECTION_REFUSED'),
    (r'Unable to get file lock', 'FILE_LOCK_ERROR'),
]

warning_patterns = [
    (r'BEA-\\d+.*Warning', 'WEBLOGIC_WARNING'),
    (r'Low memory', 'LOW_MEMORY'),
    (r'Stuck thread', 'STUCK_THREAD'),
    (r'overloaded', 'OVERLOADED'),
]

def parse_log_file(file_path, search_patterns, max_lines=5000):
    results = []
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                # Read last max_lines lines
                lines = f.readlines()[-max_lines:]
                for line_num, line in enumerate(lines):
                    for pattern, event_type in search_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Try to extract timestamp
                            timestamp_match = re.search(r'(\\d{{4}}-\\d{{2}}-\\d{{2}}[T ]\\d{{2}}:\\d{{2}}:\\d{{2}})', line)
                            timestamp = timestamp_match.group(1) if timestamp_match else 'Unknown'
                            results.append({{
                                'type': event_type,
                                'timestamp': timestamp,
                                'message': line.strip()[:500],
                                'source': os.path.basename(file_path)
                            }})
                            break
    except Exception as e:
        results.append({{'type': 'READ_ERROR', 'message': str(e), 'source': file_path}})
    return results

# Analyze NodeManager log
if '{params.log_type}' in ['all', 'nodemanager']:
    if os.path.exists(nm_log_path):
        nm_results = parse_log_file(nm_log_path, restart_patterns + error_patterns)
        for r in nm_results:
            if r['type'] in ['SERVER_START', 'SERVER_STOP', 'SERVER_STARTED', 'SERVER_STOPPED',
                            'SERVER_FAILED', 'AUTO_RESTART', 'NM_RESTART', 'PROCESS_CRASH', 'PROCESS_EXIT']:
                analysis['nodemanager_events'].append(r)
            elif 'ERROR' in r['type'] or 'CRASH' in r['type'] or 'MEMORY' in r['type']:
                analysis['errors'].append(r)
    else:
        analysis['nodemanager_events'].append({{'type': 'INFO', 'message': 'NodeManager log not found at: ' + nm_log_path}})

# Analyze server log
if '{params.log_type}' in ['all', 'server']:
    server_log = os.path.join(server_log_dir, '{params.server_name}.log')
    if os.path.exists(server_log):
        server_results = parse_log_file(server_log, error_patterns + warning_patterns + restart_patterns)
        for r in server_results:
            if 'ERROR' in r['type'] or 'CRASH' in r['type'] or 'MEMORY' in r['type'] or 'OVERFLOW' in r['type']:
                analysis['errors'].append(r)
            elif 'WARNING' in r['type'] or 'STUCK' in r['type'] or 'OVERLOAD' in r['type']:
                analysis['warnings'].append(r)
            else:
                analysis['restart_events'].append(r)

# Analyze stdout/stderr log
if '{params.log_type}' in ['all', 'stdout']:
    stdout_log = os.path.join(server_log_dir, '{params.server_name}.out')
    if os.path.exists(stdout_log):
        stdout_results = parse_log_file(stdout_log, error_patterns + restart_patterns)
        for r in stdout_results:
            if 'ERROR' in r['type'] or 'CRASH' in r['type'] or 'MEMORY' in r['type']:
                analysis['errors'].append(r)
            elif r['type'] in ['SERVER_START', 'PROCESS_CRASH', 'PROCESS_EXIT']:
                analysis['restart_events'].append(r)

# Generate summary
analysis['summary'] = {{
    'total_errors': len(analysis['errors']),
    'total_warnings': len(analysis['warnings']),
    'total_restart_events': len(analysis['restart_events']),
    'total_nm_events': len(analysis['nodemanager_events']),
    'has_oom_errors': any('MEMORY' in e['type'] for e in analysis['errors']),
    'has_jvm_crashes': any('CRASH' in e['type'] for e in analysis['errors']),
    'auto_restart_enabled': analysis['server_info'].get('auto_restart', False),
    'current_state': analysis['server_info'].get('current_state', 'UNKNOWN'),
    'nm_restart_count': analysis['server_info'].get('nm_restart_count', 0)
}}

# Determine probable restart reason
probable_reasons = []
if analysis['summary']['has_oom_errors']:
    probable_reasons.append('OutOfMemoryError - JVM ran out of heap space')
if analysis['summary']['has_jvm_crashes']:
    probable_reasons.append('JVM Crash - Native code or JVM bug')
if analysis['summary']['nm_restart_count'] > 0:
    probable_reasons.append('NodeManager triggered restart (count: ' + str(analysis['summary']['nm_restart_count']) + ')')

# Check for specific error patterns in errors list
for err in analysis['errors']:
    if 'FILE_LOCK' in err['type']:
        probable_reasons.append('File lock issue - another process may be running')
    if 'CONNECTION_REFUSED' in err['type']:
        probable_reasons.append('Connection issues - network or Admin Server problems')

analysis['summary']['probable_restart_reasons'] = probable_reasons if probable_reasons else ['No clear restart reason found in analyzed logs']

print('LOGS_JSON:' + json.dumps(analysis))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, days_to_analyze * 10 + DEFAULT_TIMEOUT)

    if not result['success']:
        return _handle_error(result)

    analysis = None
    for line in result['stdout'].split('\n'):
        if 'LOGS_JSON:' in line:
            try:
                analysis = json.loads(line.replace('LOGS_JSON:', ''))
            except:
                pass

    if not analysis:
        return "Unable to retrieve or parse log analysis results."

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(analysis, indent=2)

    # Format as Markdown
    lines = [
        f"# Log Analysis: {params.server_name}",
        "",
        f"**Time Range**: {analysis.get('time_range', {}).get('from', 'N/A')} to {analysis.get('time_range', {}).get('to', 'N/A')}",
        f"**Days Analyzed**: {days_to_analyze}",
        ""
    ]

    # Server Info
    server_info = analysis.get('server_info', {})
    lines.extend([
        "## Server Information",
        f"- **Current State**: {server_info.get('current_state', 'Unknown')}",
        f"- **NodeManager Restart Count**: {server_info.get('nm_restart_count', 0)}",
        f"- **Auto Restart Enabled**: {server_info.get('auto_restart', False)}",
        f"- **Max Restarts**: {server_info.get('restart_max', 'N/A')}",
        f"- **Restart Interval**: {server_info.get('restart_interval_seconds', 'N/A')} seconds",
        f"- **Machine**: {server_info.get('machine', 'N/A')}",
        ""
    ])

    # Summary
    summary = analysis.get('summary', {})
    lines.extend([
        "## Summary",
        f"- **Total Errors Found**: {summary.get('total_errors', 0)}",
        f"- **Total Warnings Found**: {summary.get('total_warnings', 0)}",
        f"- **Restart Events**: {summary.get('total_restart_events', 0)}",
        f"- **NodeManager Events**: {summary.get('total_nm_events', 0)}",
        f"- **OutOfMemory Errors**: {'Yes' if summary.get('has_oom_errors') else 'No'}",
        f"- **JVM Crashes**: {'Yes' if summary.get('has_jvm_crashes') else 'No'}",
        ""
    ])

    # Probable Restart Reasons
    reasons = summary.get('probable_restart_reasons', [])
    lines.extend([
        "## Probable Restart Reasons",
    ])
    if reasons:
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- No clear restart reason identified")
    lines.append("")

    # Errors
    errors = analysis.get('errors', [])
    if errors:
        lines.extend([
            "## Errors Found",
        ])
        for err in errors[:20]:  # Limit to 20
            lines.append(f"- **[{err.get('type', 'ERROR')}]** ({err.get('timestamp', 'N/A')}) - {err.get('source', 'unknown')}")
            lines.append(f"  `{err.get('message', '')[:200]}...`" if len(err.get('message', '')) > 200 else f"  `{err.get('message', '')}`")
        if len(errors) > 20:
            lines.append(f"  ... and {len(errors) - 20} more errors")
        lines.append("")

    # NodeManager Events
    nm_events = analysis.get('nodemanager_events', [])
    if nm_events:
        lines.extend([
            "## NodeManager Events",
        ])
        for evt in nm_events[:15]:  # Limit to 15
            lines.append(f"- **[{evt.get('type', 'EVENT')}]** ({evt.get('timestamp', 'N/A')})")
            if evt.get('message'):
                lines.append(f"  `{evt.get('message', '')[:150]}...`" if len(evt.get('message', '')) > 150 else f"  `{evt.get('message', '')}`")
        if len(nm_events) > 15:
            lines.append(f"  ... and {len(nm_events) - 15} more events")
        lines.append("")

    # Warnings
    warnings = analysis.get('warnings', [])
    if warnings:
        lines.extend([
            "## Warnings Found",
        ])
        for warn in warnings[:10]:  # Limit to 10
            lines.append(f"- **[{warn.get('type', 'WARNING')}]** ({warn.get('timestamp', 'N/A')}) - `{warn.get('message', '')[:100]}`")
        if len(warnings) > 10:
            lines.append(f"  ... and {len(warnings) - 10} more warnings")
        lines.append("")

    # Log paths for reference
    lines.extend([
        "## Log Paths Analyzed",
        f"- Domain Home: `{analysis.get('domain_home', 'N/A')}`",
        f"- NodeManager Log: `$DOMAIN_HOME/nodemanager/nodemanager.log`",
        f"- Server Log: `$DOMAIN_HOME/servers/{params.server_name}/logs/{params.server_name}.log`",
        f"- Server Output: `$DOMAIN_HOME/servers/{params.server_name}/logs/{params.server_name}.out`",
    ])

    return '\n'.join(lines)


@mcp.tool(
    name="wlst_diagnose_application",
    annotations={
        "title": "Diagnose Application Issues",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wlst_diagnose_application(params: AppDiagnosticInput) -> str:
    '''Diagnose why an application is in FAILED state or having issues.

    This tool performs comprehensive diagnostics on WebLogic applications including:
    - Checking current vs intended state
    - Verifying source files exist
    - Searching logs for related errors
    - Identifying probable causes
    - Providing remediation suggestions

    Args:
        params (AppDiagnosticInput): Diagnostic parameters including:
            - app_name (Optional[str]): Application to diagnose. If not provided, diagnoses all FAILED apps.
            - check_logs (bool): Whether to search logs for errors (default: True)
            - response_format: Output format (markdown or json)

    Returns:
        str: Diagnostic report with findings and recommendations
    '''
    app_filter = f"app_name = '{params.app_name}'" if params.app_name else "app_name = None"
    check_logs_flag = "True" if params.check_logs else "False"

    script = f'''
import json
import os
import re

{_build_connect_script(params.get_admin_url(), params.get_username(), params.get_password())}

diagnostics = {{
    'apps_analyzed': [],
    'summary': {{
        'total_analyzed': 0,
        'total_failed': 0,
        'total_issues_found': 0
    }}
}}

# Get domain home
serverConfig()
domainHome = str(cmo.getRootDirectory())
diagnostics['domain_home'] = domainHome

# Get all app deployments info
cd('AppDeployments')
appDeploymentsRaw = ls(returnMap='true')
appDeploymentsList = list(appDeploymentsRaw) if appDeploymentsRaw else []

# Build app config map
appConfigMap = {{}}
for appName in appDeploymentsList:
    cd(appName)
    appConfigMap[str(appName)] = {{
        'sourcePath': str(cmo.getSourcePath()) if cmo.getSourcePath() else '',
        'stagingMode': str(cmo.getStagingMode()) if cmo.getStagingMode() else 'default',
        'planPath': str(cmo.getPlanPath()) if cmo.getPlanPath() else None,
        'deploymentOrder': cmo.getDeploymentOrder()
    }}
    # Get targets
    cd('Targets')
    targetsRaw = ls(returnMap='true')
    appConfigMap[str(appName)]['targets'] = [str(t) for t in list(targetsRaw)] if targetsRaw else []
    cd('../..')

# Get runtime states
domainRuntime()
cd('AppRuntimeStateRuntime/AppRuntimeStateRuntime')
appNamesRaw = cmo.getApplicationIds()
appNamesList = list(appNamesRaw) if appNamesRaw else []

# Filter apps to analyze
{app_filter}
if app_name:
    apps_to_analyze = [app_name] if app_name in appNamesList else []
    if not apps_to_analyze:
        print('DIAG_JSON:' + json.dumps({{'error': 'Application not found: ' + app_name}}))
        disconnect()
        exit()
else:
    # Find all FAILED apps
    apps_to_analyze = []
    for appName in appNamesList:
        targets = appConfigMap.get(str(appName), {{}}).get('targets', [])
        for target in targets:
            try:
                state = str(cmo.getCurrentState(str(appName), str(target)))
                if 'FAILED' in state.upper():
                    if str(appName) not in apps_to_analyze:
                        apps_to_analyze.append(str(appName))
            except:
                pass

diagnostics['summary']['total_analyzed'] = len(apps_to_analyze)

# Analyze each app
for appName in apps_to_analyze:
    appDiag = {{
        'name': appName,
        'issues': [],
        'probable_causes': [],
        'suggestions': [],
        'log_errors': []
    }}

    config = appConfigMap.get(appName, {{}})
    appDiag['config'] = config

    # Get current state per target
    targets = config.get('targets', [])
    target_states = []
    for target in targets:
        try:
            state = str(cmo.getCurrentState(appName, target))
            target_states.append({{'target': target, 'state': state}})
        except Exception as e:
            target_states.append({{'target': target, 'state': 'ERROR', 'error': str(e)}})

    appDiag['target_states'] = target_states
    appDiag['intended_state'] = str(cmo.getIntendedState(appName))

    # Check if any target is FAILED
    has_failed = any('FAILED' in ts.get('state', '').upper() for ts in target_states)
    if has_failed:
        diagnostics['summary']['total_failed'] += 1

    # DIAGNOSTIC 1: Check if source file exists
    sourcePath = config.get('sourcePath', '')
    if sourcePath:
        # Handle relative paths
        if not os.path.isabs(sourcePath):
            fullPath = os.path.join(domainHome, sourcePath)
        else:
            fullPath = sourcePath

        appDiag['source_path_full'] = fullPath
        source_exists = os.path.exists(fullPath)
        appDiag['source_exists'] = source_exists

        if not source_exists:
            appDiag['issues'].append('SOURCE_FILE_MISSING')
            appDiag['probable_causes'].append('The application source file (WAR/EAR) does not exist at: ' + fullPath)
            appDiag['suggestions'].append('Re-deploy the application with a valid source file path')
            appDiag['suggestions'].append('Or copy the application archive to: ' + fullPath)
            diagnostics['summary']['total_issues_found'] += 1
    else:
        appDiag['issues'].append('NO_SOURCE_PATH')
        appDiag['probable_causes'].append('Application has no source path configured')

    # DIAGNOSTIC 2: Check staging directory if staging mode is used
    stagingMode = config.get('stagingMode', '')
    if stagingMode and stagingMode.lower() == 'stage':
        for target in targets:
            stagePath = os.path.join(domainHome, 'servers', target, 'stage', appName)
            if os.path.exists(stagePath):
                appDiag['staging_path'] = stagePath
                appDiag['staging_exists'] = True
            else:
                appDiag['staging_exists'] = False
                if 'SOURCE_FILE_MISSING' not in appDiag['issues']:
                    appDiag['issues'].append('STAGING_MISSING')
                    appDiag['probable_causes'].append('Staged files not found at: ' + stagePath)

    # DIAGNOSTIC 3: Search logs for errors (if enabled)
    check_logs = {check_logs_flag}
    if check_logs and has_failed:
        log_errors = []
        appNameLower = appName.lower()

        # Search in server logs for each target
        for target in targets:
            server_log = os.path.join(domainHome, 'servers', target, 'logs', target + '.log')
            server_out = os.path.join(domainHome, 'servers', target, 'logs', target + '.out')

            for log_file in [server_log, server_out]:
                if os.path.exists(log_file):
                    try:
                        f = open(log_file, 'r')
                        lines = f.readlines()
                        f.close()
                        # Search last 2000 lines
                        for line in lines[-2000:]:
                            lineLower = line.lower()
                            if appNameLower in lineLower:
                                # Check for error indicators
                                if any(err in lineLower for err in ['error', 'exception', 'failed', 'unable']):
                                    log_errors.append({{
                                        'source': os.path.basename(log_file),
                                        'message': line.strip()[:300]
                                    }})
                                    if len(log_errors) >= 10:
                                        break
                    except:
                        pass
                if len(log_errors) >= 10:
                    break

        # Also search AdminServer log
        admin_log = os.path.join(domainHome, 'servers', 'AdminServer', 'logs', 'AdminServer.log')
        if os.path.exists(admin_log) and len(log_errors) < 10:
            try:
                f = open(admin_log, 'r')
                lines = f.readlines()
                f.close()
                for line in lines[-1000:]:
                    lineLower = line.lower()
                    if appNameLower in lineLower:
                        if any(err in lineLower for err in ['error', 'exception', 'failed', 'unable', 'bea-149']):
                            log_errors.append({{
                                'source': 'AdminServer.log',
                                'message': line.strip()[:300]
                            }})
                            if len(log_errors) >= 10:
                                break
            except:
                pass

        appDiag['log_errors'] = log_errors

        # Analyze log errors for common patterns
        for err in log_errors:
            msg = err.get('message', '').lower()
            if 'classnotfound' in msg or 'noclassdeffounderror' in msg:
                if 'CLASS_NOT_FOUND' not in appDiag['issues']:
                    appDiag['issues'].append('CLASS_NOT_FOUND')
                    appDiag['probable_causes'].append('Missing class or JAR dependency')
                    appDiag['suggestions'].append('Check application dependencies and ensure all required JARs are included')
            elif 'outofmemory' in msg:
                if 'OUT_OF_MEMORY' not in appDiag['issues']:
                    appDiag['issues'].append('OUT_OF_MEMORY')
                    appDiag['probable_causes'].append('JVM ran out of memory during deployment')
                    appDiag['suggestions'].append('Increase JVM heap size (-Xmx) for the target server')
            elif 'connection refused' in msg or 'socket' in msg:
                if 'CONNECTION_ERROR' not in appDiag['issues']:
                    appDiag['issues'].append('CONNECTION_ERROR')
                    appDiag['probable_causes'].append('Network or database connection issue during startup')
                    appDiag['suggestions'].append('Verify database/external service connectivity')
            elif 'duplicate' in msg or 'already exists' in msg:
                if 'DUPLICATE_RESOURCE' not in appDiag['issues']:
                    appDiag['issues'].append('DUPLICATE_RESOURCE')
                    appDiag['probable_causes'].append('Duplicate resource or naming conflict')
                    appDiag['suggestions'].append('Check for duplicate JNDI names or resource definitions')

    # Add generic suggestions if no specific issues found
    if not appDiag['issues'] and has_failed:
        appDiag['issues'].append('UNKNOWN')
        appDiag['probable_causes'].append('Could not determine specific cause from available information')
        appDiag['suggestions'].append('Check server logs manually for detailed error messages')
        appDiag['suggestions'].append('Try to redeploy the application')
        appDiag['suggestions'].append('Verify all application dependencies are available')

    diagnostics['apps_analyzed'].append(appDiag)

print('DIAG_JSON:' + json.dumps(diagnostics))
{_build_disconnect_script()}
'''

    result = await _execute_wlst_script(script, DEFAULT_TIMEOUT * 2)

    if not result['success']:
        return _handle_error(result)

    diagnostics = None
    for line in result['stdout'].split('\n'):
        if 'DIAG_JSON:' in line:
            try:
                diagnostics = json.loads(line.replace('DIAG_JSON:', ''))
            except:
                pass

    if not diagnostics:
        return "Unable to retrieve diagnostic information."

    if 'error' in diagnostics:
        return f"Error: {diagnostics['error']}"

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(diagnostics, indent=2)

    # Format as Markdown
    lines = ["# Application Diagnostics Report", ""]

    summary = diagnostics.get('summary', {})
    lines.extend([
        "## Summary",
        f"- **Applications Analyzed**: {summary.get('total_analyzed', 0)}",
        f"- **Applications in FAILED State**: {summary.get('total_failed', 0)}",
        f"- **Total Issues Found**: {summary.get('total_issues_found', 0)}",
        ""
    ])

    if not diagnostics.get('apps_analyzed'):
        if params.app_name:
            lines.append(f"Application **{params.app_name}** was not found or has no issues.")
        else:
            lines.append("No applications in FAILED state were found.")
        return '\n'.join(lines)

    for app in diagnostics.get('apps_analyzed', []):
        app_name = app.get('name', 'Unknown')
        issues = app.get('issues', [])

        # Determine status emoji
        if 'SOURCE_FILE_MISSING' in issues:
            status_emoji = "🔴"
        elif issues and issues != ['UNKNOWN']:
            status_emoji = "🟠"
        elif not issues:
            status_emoji = "🟢"
        else:
            status_emoji = "🟡"

        lines.extend([
            f"## {status_emoji} {app_name}",
            ""
        ])

        # Current state
        lines.append("### State")
        for ts in app.get('target_states', []):
            state_emoji = "🟢" if ts.get('state') == 'STATE_ACTIVE' else "🔴" if 'FAILED' in ts.get('state', '').upper() else "🟡"
            lines.append(f"- {state_emoji} **{ts.get('target')}**: {ts.get('state')}")
        lines.append(f"- **Intended State**: {app.get('intended_state', 'N/A')}")
        lines.append("")

        # Source file check
        lines.append("### Source File")
        source_path = app.get('source_path_full', app.get('config', {}).get('sourcePath', 'N/A'))
        source_exists = app.get('source_exists', None)
        if source_exists is True:
            lines.append(f"- ✅ **Path**: `{source_path}`")
            lines.append("- ✅ **File Exists**: Yes")
        elif source_exists is False:
            lines.append(f"- **Path**: `{source_path}`")
            lines.append("- ❌ **File Exists**: No")
        else:
            lines.append(f"- **Path**: `{source_path}`")
        lines.append("")

        # Issues found
        if issues:
            lines.append("### Issues Found")
            issue_descriptions = {
                'SOURCE_FILE_MISSING': '❌ Source file (WAR/EAR) not found on filesystem',
                'NO_SOURCE_PATH': '⚠️ No source path configured',
                'STAGING_MISSING': '⚠️ Staged files not found',
                'CLASS_NOT_FOUND': '❌ Missing class or JAR dependency',
                'OUT_OF_MEMORY': '❌ Out of memory during deployment',
                'CONNECTION_ERROR': '❌ Connection error (database/network)',
                'DUPLICATE_RESOURCE': '⚠️ Duplicate resource or naming conflict',
                'UNKNOWN': '❓ Unknown issue - manual investigation needed'
            }
            for issue in issues:
                lines.append(f"- {issue_descriptions.get(issue, issue)}")
            lines.append("")

        # Probable causes
        causes = app.get('probable_causes', [])
        if causes:
            lines.append("### Probable Causes")
            for cause in causes:
                lines.append(f"- {cause}")
            lines.append("")

        # Suggestions
        suggestions = app.get('suggestions', [])
        if suggestions:
            lines.append("### Recommendations")
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"{i}. {suggestion}")
            lines.append("")

        # Log errors
        log_errors = app.get('log_errors', [])
        if log_errors:
            lines.append("### Related Log Entries")
            for err in log_errors[:5]:  # Show max 5
                lines.append(f"- **[{err.get('source', 'unknown')}]**")
                lines.append(f"  ```")
                lines.append(f"  {err.get('message', '')[:200]}")
                lines.append(f"  ```")
            if len(log_errors) > 5:
                lines.append(f"- ... and {len(log_errors) - 5} more entries")
            lines.append("")

    # Footer
    lines.extend([
        "---",
        f"*Domain: `{diagnostics.get('domain_home', 'N/A')}`*"
    ])

    return '\n'.join(lines)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
