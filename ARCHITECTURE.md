# WLST MCP Server - Architecture

## System Overview

This document describes how the WLST MCP Server integrates with Claude and WebLogic Server.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   USER                                          │
│                                                                                 │
│    ┌──────────────────────┐              ┌──────────────────────┐              │
│    │   Claude Desktop     │              │    Claude Code       │              │
│    │   (GUI Application)  │              │    (CLI Terminal)    │              │
│    │                      │              │                      │              │
│    │  ┌────────────────┐  │              │  $ claude            │              │
│    │  │ Chat Interface │  │              │  > List servers      │              │
│    │  │                │  │              │  > Start server      │              │
│    │  │ "List servers" │  │              │  > Deploy app        │              │
│    │  └────────────────┘  │              │                      │              │
│    └──────────┬───────────┘              └──────────┬───────────┘              │
│               │                                     │                          │
│               │         Natural Language            │                          │
│               │            Requests                 │                          │
│               └──────────────────┬──────────────────┘                          │
│                                  │                                              │
└──────────────────────────────────┼──────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         MODEL CONTEXT PROTOCOL (MCP)                             │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                         WLST MCP Server                                    │  │
│  │                         (wlst_mcp.py)                                      │  │
│  │                                                                            │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐         │  │
│  │  │ Connection  │ │   Server    │ │ Application │ │  Resource   │         │  │
│  │  │   Tools     │ │   Tools     │ │   Tools     │ │   Tools     │         │  │
│  │  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤         │  │
│  │  │test_conn    │ │start_server │ │deploy       │ │list_ds      │         │  │
│  │  │list_servers │ │stop_server  │ │undeploy     │ │list_jms     │         │  │
│  │  │             │ │restart      │ │list_apps    │ │             │         │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘         │  │
│  │                                                                            │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────────────┐         │  │
│  │  │ Monitoring  │ │ Diagnostics │ │    Environment Variables     │         │  │
│  │  │   Tools     │ │   Tools     │ │                              │         │  │
│  │  ├─────────────┤ ├─────────────┤ │  WLST_ADMIN_URL=t3://...    │         │  │
│  │  │server_health│ │thread_dump  │ │  WLST_USERNAME=weblogic      │         │  │
│  │  │server_metric│ │exec_script  │ │  WLST_PASSWORD=*****         │         │  │
│  │  └─────────────┘ └─────────────┘ └──────────────────────────────┘         │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                            │
│                                     │  Generates WLST/Jython Scripts             │
│                                     ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                              WLST                                          │  │
│  │                    (WebLogic Scripting Tool)                               │  │
│  │                                                                            │  │
│  │    ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │    │  wlst.cmd / wlst.sh                                             │    │  │
│  │    │                                                                 │    │  │
│  │    │  connect('weblogic', 'pass', 't3://localhost:7001')            │    │  │
│  │    │  domainRuntime()                                                │    │  │
│  │    │  cd('ServerRuntimes')                                           │    │  │
│  │    │  ...                                                            │    │  │
│  │    └─────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                            │
└─────────────────────────────────────┼────────────────────────────────────────────┘
                                      │
                                      │  T3/T3S/HTTP/HTTPS Protocol
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           ORACLE WEBLOGIC SERVER                                 │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           WebLogic Domain                                 │   │
│  │                          (base_domain)                                    │   │
│  │                                                                           │   │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │   │
│  │   │  Admin Server   │    │ Managed Server  │    │ Managed Server  │      │   │
│  │   │                 │    │                 │    │                 │      │   │
│  │   │  Port: 7001     │    │  test_server1   │    │  test_server2   │      │   │
│  │   │  State: RUNNING │    │  State: RUNNING │    │  State: SHUTDOWN│      │   │
│  │   │                 │    │                 │    │                 │      │   │
│  │   │  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │      │   │
│  │   │  │ Console   │  │    │  │   Apps    │  │    │  │   Apps    │  │      │   │
│  │   │  │ MBeans    │  │    │  │ Datasource│  │    │  │ Datasource│  │      │   │
│  │   │  │ Config    │  │    │  │ JMS       │  │    │  │ JMS       │  │      │   │
│  │   │  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │      │   │
│  │   └─────────────────┘    └─────────────────┘    └─────────────────┘      │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST FLOW                                       │
│                                                                                 │
│  1. USER                    2. CLAUDE                   3. MCP SERVER          │
│  ┌─────────┐               ┌─────────┐                 ┌─────────┐             │
│  │ "List   │ ──────────▶  │ Process │ ──────────▶    │ Execute │             │
│  │ servers"│   Natural    │ Request │   MCP Tool     │ WLST    │             │
│  └─────────┘   Language   └─────────┘   Call         └────┬────┘             │
│                                                            │                   │
│                                                            ▼                   │
│  6. USER                    5. CLAUDE                  4. WEBLOGIC            │
│  ┌─────────┐               ┌─────────┐                 ┌─────────┐            │
│  │ View    │ ◀──────────  │ Format  │ ◀──────────    │ Return  │            │
│  │ Results │   Formatted  │ Response│   JSON/Text    │ Data    │            │
│  └─────────┘   Output     └─────────┘                └─────────┘            │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **User** | Sends natural language requests via Claude Desktop or Claude Code |
| **Claude** | Interprets requests and calls appropriate MCP tools |
| **MCP Server** | Translates tool calls to WLST scripts and executes them |
| **WLST** | Oracle's scripting tool that communicates with WebLogic |
| **WebLogic** | Application server being managed |

## Connection Protocols

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│  Claude        │     │  MCP Server    │     │  WebLogic      │
│  Desktop/Code  │────▶│  (Python)      │────▶│  Admin Server  │
└────────────────┘     └────────────────┘     └────────────────┘
        │                      │                      │
        │   stdio/IPC          │   T3/T3S/HTTP       │
        │                      │                      │
        └──────────────────────┴──────────────────────┘

Protocol Options:
• t3://   - Oracle T3 (fast, default)
• t3s://  - Oracle T3 over SSL (secure)
• http:// - HTTP tunneling (firewall-friendly)
• https://- HTTPS tunneling (secure + firewall-friendly)
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        SECURITY MODEL                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 1: Claude Authentication                          │    │
│  │ • User authenticates with Claude Desktop/Code           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 2: Environment Variables                          │    │
│  │ • WLST_USERNAME / WLST_PASSWORD                         │    │
│  │ • Stored securely, not in code                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 3: WebLogic Authentication                        │    │
│  │ • Admin credentials validated by WebLogic               │    │
│  │ • Role-based access (Admin, Operator, Deployer)         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Layer 4: Network Security                               │    │
│  │ • T3S/HTTPS for encrypted communication                 │    │
│  │ • Firewall rules for Admin Server access                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```
