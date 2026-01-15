# WLST MCP Server - Usage Examples

This document provides practical examples for using the WLST MCP Server tools.

## Table of Contents

- [Server Management](#server-management)
- [Monitoring & Metrics](#monitoring--metrics)
- [Application Deployment](#application-deployment)
- [Resource Management](#resource-management)
- [Custom Scripts](#custom-scripts)

---

## Server Management

### List All Servers

**User prompt:**
> "Show me all WebLogic servers and their status"

> "List the servers in my domain"

**Example Output:**
```markdown
# WebLogic Servers

**Total servers**: 2

- 🟢 **AdminServer**: RUNNING
- 🟢 **test_server1**: RUNNING
```

---

### Start a Managed Server

**User prompt:**
> "Start the server test_server1"

> "Bring up test_server1"

**Example Output:**
```
Server **test_server1** started successfully.
```

---

### Stop a Managed Server

The stop operation supports two modes:

#### Graceful Shutdown (Default)

Waits for active sessions to complete before stopping. Recommended for production environments.

**User prompt:**
> "Stop the server test_server1"

> "Shut down test_server1 gracefully"

> "Stop test_server1 and wait for sessions to finish"

**Example Output:**
```
Server **test_server1** stopped successfully.
```

#### Force Shutdown

Stops the server immediately without waiting for sessions. Use when the server is unresponsive or you need to stop quickly.

**User prompt:**
> "Force stop the server test_server1"

> "Stop test_server1 immediately"

> "Kill the server test_server1 right now"

> "Shut down test_server1 without waiting"

**Example Output:**
```
Server **test_server1** stopped successfully.
```

#### Shutdown Comparison

| Mode | When to Use | User Prompt Examples |
|------|-------------|---------------------|
| **Graceful** | Normal operations, scheduled maintenance | "Stop test_server1", "Shut down gracefully" |
| **Force** | Emergency, unresponsive server, quick restart needed | "Force stop", "Stop immediately", "Kill the server" |

---

### Restart a Server

**User prompt:**
> "Restart the server test_server1"

> "Reboot test_server1"

For a quick restart with force shutdown:
> "Force restart test_server1"

> "Restart test_server1 immediately"

**Example Output:**
```
Server **test_server1** restarted successfully.
```

---

## Monitoring & Metrics

### Check Server Health

```json
{
  "tool": "wlst_server_health",
  "params": {
    "server_name": "test_server1"
  }
}
```

**Example Output:**
```markdown
# Server Health Status

## 🟢 test_server1
- **State**: RUNNING
- **Health**: HEALTH_OK
- **Open Sockets**: 6
```

### Get All Metrics

```json
{
  "tool": "wlst_server_metrics",
  "params": {
    "server_name": "test_server1",
    "metric_type": "all"
  }
}
```

### Get JVM Metrics Only

```json
{
  "tool": "wlst_server_metrics",
  "params": {
    "server_name": "test_server1",
    "metric_type": "jvm"
  }
}
```

### Get Thread Metrics Only

```json
{
  "tool": "wlst_server_metrics",
  "params": {
    "server_name": "test_server1",
    "metric_type": "threads"
  }
}
```

### Capture Thread Dump

```json
{
  "tool": "wlst_thread_dump",
  "params": {
    "server_name": "test_server1"
  }
}
```

---

## Application Deployment

### Deploy an Application

```json
{
  "tool": "wlst_deploy",
  "params": {
    "app_name": "myapp",
    "app_path": "/path/to/myapp.war",
    "targets": "test_server1"
  }
}
```

### Deploy to Multiple Targets

```json
{
  "tool": "wlst_deploy",
  "params": {
    "app_name": "myapp",
    "app_path": "/path/to/myapp.ear",
    "targets": "test_server1,test_server2,Cluster1"
  }
}
```

### Deploy with Deployment Plan

```json
{
  "tool": "wlst_deploy",
  "params": {
    "app_name": "myapp",
    "app_path": "/path/to/myapp.ear",
    "targets": "test_server1",
    "plan_path": "/path/to/plan.xml",
    "stage_mode": "stage"
  }
}
```

### Undeploy an Application

```json
{
  "tool": "wlst_undeploy",
  "params": {
    "app_name": "myapp"
  }
}
```

### List All Applications

**User prompt:**
> "List all deployed applications"

> "Show me what apps are running"

```json
{
  "tool": "wlst_list_applications",
  "params": {}
}
```

**Example Output:**
```markdown
# WebLogic Applications

**Total applications**: 2

## 🟢 **SampleWebApp**
- **Type**: war
- **State**: STATE_ACTIVE
- **Targets**: test_server1

## 🔴 **myapp**
- **Type**: war
- **State**: STATE_PREPARED
- **Targets**: test_server1
```

---

### Start an Application

Start a deployed application that is in a stopped (prepared) state.

**User prompt:**
> "Start the application myapp"

> "Bring up myapp"

> "Activate the application myapp"

```json
{
  "tool": "wlst_start_application",
  "params": {
    "app_name": "myapp"
  }
}
```

**Example Output:**
```
Application **myapp** started successfully.
```

---

### Stop an Application

Stop a running application without undeploying it. The application remains deployed but inactive.

**User prompt:**
> "Stop the application myapp"

> "Deactivate myapp"

> "Take myapp offline"

```json
{
  "tool": "wlst_stop_application",
  "params": {
    "app_name": "myapp"
  }
}
```

**Example Output:**
```
Application **myapp** stopped successfully.
```

---

### Redeploy an Application

Update an application in place without undeploying it first. Useful for applying changes to an already deployed application.

**User prompt:**
> "Redeploy the application myapp"

> "Update myapp in place"

> "Refresh myapp deployment"

```json
{
  "tool": "wlst_redeploy_application",
  "params": {
    "app_name": "myapp"
  }
}
```

**Example Output:**
```
Application **myapp** redeployed successfully.
```

---

### Application Lifecycle Comparison

| Operation | Use Case | Result |
|-----------|----------|--------|
| **Deploy** | Initial deployment of a new application | App deployed and started |
| **Start** | Activate a stopped application | App state changes to ACTIVE |
| **Stop** | Temporarily deactivate an application | App state changes to PREPARED |
| **Redeploy** | Update application with new version | App refreshed in place |
| **Undeploy** | Remove application completely | App removed from domain |

---

## Resource Management

### List JDBC Datasources

```json
{
  "tool": "wlst_list_datasources",
  "params": {}
}
```

### List JMS Resources

```json
{
  "tool": "wlst_list_jms_resources",
  "params": {}
}
```

---

## Custom Scripts

### Get Server State and Health

```json
{
  "tool": "wlst_execute_script",
  "params": {
    "script": "domainRuntime()\ncd('ServerRuntimes')\nservers = ls(returnMap='true')\nfor server in servers:\n    cd(server)\n    print('Server: ' + server)\n    print('State: ' + str(get('State')))\n    print('Health: ' + str(get('HealthState')))\n    cd('..')"
  }
}
```

**Example Output:**
```
Server: AdminServer
State: RUNNING
Health: Component:ServerRuntime,State:HEALTH_OK

Server: test_server1
State: RUNNING
Health: Component:ServerRuntime,State:HEALTH_OK
```

### Get Detailed JVM Metrics

```json
{
  "tool": "wlst_execute_script",
  "params": {
    "script": "domainRuntime()\ncd('ServerRuntimes/test_server1/JVMRuntime/test_server1')\nprint('=== JVM Metrics ===')\nprint('Heap Size Current: ' + str(get('HeapSizeCurrent') / (1024*1024)) + ' MB')\nprint('Heap Size Max: ' + str(get('HeapSizeMax') / (1024*1024)) + ' MB')\nprint('Heap Free Current: ' + str(get('HeapFreeCurrent') / (1024*1024)) + ' MB')\nprint('Heap Free Percent: ' + str(get('HeapFreePercent')) + '%')\nprint('Uptime: ' + str(get('Uptime') / 1000) + ' seconds')\nprint('Java Version: ' + str(get('JavaVersion')))"
  }
}
```

**Example Output:**
```
=== JVM Metrics ===
Heap Size Current: 256 MB
Heap Size Max: 512 MB
Heap Free Current: 106 MB
Heap Free Percent: 70%
Uptime: 886 seconds
Java Version: 11.0.15.1
```

### Get Thread Pool Metrics

```json
{
  "tool": "wlst_execute_script",
  "params": {
    "script": "domainRuntime()\ncd('ServerRuntimes/test_server1/ThreadPoolRuntime/ThreadPoolRuntime')\nprint('=== Thread Pool Metrics ===')\nprint('Execute Thread Total Count: ' + str(get('ExecuteThreadTotalCount')))\nprint('Execute Thread Idle Count: ' + str(get('ExecuteThreadIdleCount')))\nprint('Standby Thread Count: ' + str(get('StandbyThreadCount')))\nprint('Hogging Thread Count: ' + str(get('HoggingThreadCount')))\nprint('Pending User Request Count: ' + str(get('PendingUserRequestCount')))\nprint('Queue Length: ' + str(get('QueueLength')))\nprint('Completed Request Count: ' + str(get('CompletedRequestCount')))\nprint('Throughput: ' + str(get('Throughput')))"
  }
}
```

**Example Output:**
```
=== Thread Pool Metrics ===
Execute Thread Total Count: 13
Execute Thread Idle Count: 1
Standby Thread Count: 11
Hogging Thread Count: 0
Pending User Request Count: 0
Queue Length: 0
Completed Request Count: 6401
Throughput: 5.99
```

### Get Complete Server Metrics

```json
{
  "tool": "wlst_execute_script",
  "params": {
    "script": "domainRuntime()\nserverName = 'test_server1'\n\n# JVM Metrics\ncd('ServerRuntimes/' + serverName + '/JVMRuntime/' + serverName)\nprint('=== JVM Metrics ===')\nprint('Heap Size Current: ' + str(get('HeapSizeCurrent') / (1024*1024)) + ' MB')\nprint('Heap Size Max: ' + str(get('HeapSizeMax') / (1024*1024)) + ' MB')\nprint('Heap Free Current: ' + str(get('HeapFreeCurrent') / (1024*1024)) + ' MB')\nprint('Heap Free Percent: ' + str(get('HeapFreePercent')) + '%')\nprint('Uptime: ' + str(get('Uptime') / 1000) + ' seconds')\nprint('Java Version: ' + str(get('JavaVersion')))\n\n# Thread Pool Metrics\ncd('/ServerRuntimes/' + serverName + '/ThreadPoolRuntime/ThreadPoolRuntime')\nprint('')\nprint('=== Thread Pool Metrics ===')\nprint('Execute Thread Total Count: ' + str(get('ExecuteThreadTotalCount')))\nprint('Standby Thread Count: ' + str(get('StandbyThreadCount')))\nprint('Hogging Thread Count: ' + str(get('HoggingThreadCount')))\nprint('Completed Request Count: ' + str(get('CompletedRequestCount')))\nprint('Throughput: ' + str(get('Throughput')))\n\n# Server State\ncd('/ServerRuntimes/' + serverName)\nprint('')\nprint('=== Server State ===')\nprint('State: ' + str(get('State')))\nprint('Health: ' + str(get('HealthState')))\nprint('Open Sockets: ' + str(get('OpenSocketsCurrentCount')))"
  }
}
```

### Check Datasources Configuration

```json
{
  "tool": "wlst_execute_script",
  "params": {
    "script": "serverConfig()\ncd('/JDBCSystemResources')\nprint('=== JDBC System Resources ===')\nresources = ls(returnMap='true')\nif len(resources) == 0:\n    print('No datasources configured')\nelse:\n    for res in resources:\n        print('Datasource: ' + res)\n        cd(res + '/JDBCResource/' + res + '/JDBCDriverParams/' + res)\n        print('  URL: ' + str(get('Url')))\n        cd('/JDBCSystemResources/' + res)\n        targets = get('Targets')\n        print('  Targets: ' + str(targets))\n        cd('/JDBCSystemResources')"
  }
}
```

### Check Runtime Datasources on a Server

```json
{
  "tool": "wlst_execute_script",
  "params": {
    "script": "domainRuntime()\ncd('/ServerRuntimes/test_server1')\nprint('=== JDBC Runtime on test_server1 ===')\ntry:\n    cd('JDBCServiceRuntime/test_server1/JDBCDataSourceRuntimeMBeans')\n    ds = ls(returnMap='true')\n    if len(ds) == 0:\n        print('No datasources deployed')\n    else:\n        for d in ds:\n            cd(d)\n            print('Datasource: ' + d)\n            print('  State: ' + str(get('State')))\n            print('  Active Connections: ' + str(get('ActiveConnectionsCurrentCount')))\n            cd('..')\nexcept:\n    print('No JDBC runtime available')"
  }
}
```

---

## Tips & Best Practices

### 1. Use Environment Variables

Set default connection parameters to avoid repetition:

```bash
export WLST_ADMIN_URL=t3://localhost:7001
export WLST_USERNAME=weblogic
export WLST_PASSWORD=welcome1
```

### 2. JSON Output for Automation

Use `response_format: "json"` when integrating with automation tools:

```json
{
  "tool": "wlst_list_servers",
  "params": {
    "response_format": "json"
  }
}
```

### 3. Custom Scripts for Complex Operations

When built-in tools don't provide enough detail, use `wlst_execute_script` with custom WLST/Jython code for full control over WebLogic MBeans.

### 4. Timeouts for Long Operations

Server shutdown and restart operations have a default timeout of **300 seconds** to accommodate graceful shutdowns that wait for sessions to complete.

For other operations that may take longer (deployments, server starts), you can increase the timeout:

**User prompt:**
> "Start the server managed_server1 with a timeout of 5 minutes"

### 5. Graceful vs Force Shutdown

Choose the right shutdown mode for your situation:

| Situation | Recommended Mode | User Prompt |
|-----------|-----------------|-------------|
| Scheduled maintenance | Graceful (default) | "Stop the server" |
| Server is unresponsive | Force | "Force stop the server" |
| Quick restart needed | Force | "Restart the server immediately" |
| Production with active users | Graceful (default) | "Stop the server gracefully" |
| Emergency situation | Force | "Kill the server now" |
