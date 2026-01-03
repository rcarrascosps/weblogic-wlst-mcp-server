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

```json
{
  "tool": "wlst_list_servers",
  "params": {}
}
```

**Example Output:**
```markdown
# WebLogic Servers

**Total servers**: 2

- 🟢 **AdminServer**: RUNNING
- 🟢 **test_server1**: RUNNING
```

### Start a Managed Server

```json
{
  "tool": "wlst_start_server",
  "params": {
    "server_name": "test_server1"
  }
}
```

**Example Output:**
```
Server **test_server1** started successfully.
```

### Stop a Managed Server

```json
{
  "tool": "wlst_stop_server",
  "params": {
    "server_name": "test_server1"
  }
}
```

### Force Stop a Server

```json
{
  "tool": "wlst_stop_server",
  "params": {
    "server_name": "test_server1",
    "force": true
  }
}
```

### Restart a Server

```json
{
  "tool": "wlst_restart_server",
  "params": {
    "server_name": "test_server1"
  }
}
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

```json
{
  "tool": "wlst_list_applications",
  "params": {}
}
```

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

For operations that may take longer (deployments, server starts), increase the timeout:

```json
{
  "tool": "wlst_start_server",
  "params": {
    "server_name": "managed_server1",
    "timeout": 300
  }
}
```
