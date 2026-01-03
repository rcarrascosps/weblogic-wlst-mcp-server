# WLST MCP Server - Installation Guide

This guide provides step-by-step instructions for installing and configuring the WLST MCP Server.

## Prerequisites

### 1. Oracle WebLogic Server

A running Oracle WebLogic Server installation is required. The MCP server connects to the WebLogic Admin Server to perform administrative operations.

**Supported Versions:**

| WebLogic Version | Status | Notes |
|------------------|--------|-------|
| WebLogic 14c (14.1.1.x) | Recommended | Full support, latest features |
| WebLogic 12c (12.2.1.4) | Supported | LTS version |
| WebLogic 12c (12.2.1.3) | Supported | Minimum recommended |
| WebLogic 12c (12.1.3.x) | Limited | Legacy support |

**Installation:**
- Download from [Oracle Technology Network](https://www.oracle.com/middleware/technologies/weblogic-server-downloads.html)
- Oracle account required for download
- Follow Oracle's installation documentation

**Minimum Requirements:**
- Admin Server must be running and accessible
- At least one domain configured
- Admin user with appropriate privileges

---

### 2. Java Development Kit (JDK)

WebLogic Server and WLST require a compatible JDK installation.

**Supported JDK Versions:**

| WebLogic Version | JDK 8 | JDK 11 | JDK 17 |
|------------------|-------|--------|--------|
| 14.1.1.x | Yes | Yes | Yes |
| 12.2.1.4 | Yes | Yes | No |
| 12.2.1.3 | Yes | No | No |

**Required Environment Variables:**

```bash
# Linux/macOS
export JAVA_HOME=/path/to/jdk
export PATH=$JAVA_HOME/bin:$PATH

# Windows
set JAVA_HOME=C:\Program Files\Java\jdk-11
set PATH=%JAVA_HOME%\bin;%PATH%
```

**Verify Installation:**

```bash
java -version
# Expected output: java version "11.0.x" or "1.8.x"
```

---

### 3. Oracle Home & WLST

WLST (WebLogic Scripting Tool) is included with WebLogic Server. It's a command-line scripting environment based on Jython.

**Required Environment Variables:**

```bash
# Linux/macOS
export ORACLE_HOME=/path/to/oracle/middleware/oracle_home
export WL_HOME=$ORACLE_HOME/wlserver
export MW_HOME=$ORACLE_HOME

# Windows
set ORACLE_HOME=C:\Oracle\Middleware\Oracle_Home
set WL_HOME=%ORACLE_HOME%\wlserver
set MW_HOME=%ORACLE_HOME%
```

**WLST Location:**

| OS | Path |
|----|------|
| Linux/macOS | `$ORACLE_HOME/oracle_common/common/bin/wlst.sh` |
| Windows | `%ORACLE_HOME%\oracle_common\common\bin\wlst.cmd` |

**Verify WLST Installation:**

```bash
# Linux/macOS
$ORACLE_HOME/oracle_common/common/bin/wlst.sh -v

# Windows
%ORACLE_HOME%\oracle_common\common\bin\wlst.cmd -v
```

---

### 4. Python Environment

The MCP server requires Python 3.8 or higher.

**Supported Versions:**

| Python Version | Status |
|----------------|--------|
| Python 3.12 | Supported |
| Python 3.11 | Recommended |
| Python 3.10 | Supported |
| Python 3.9 | Supported |
| Python 3.8 | Minimum |

**Verify Installation:**

```bash
python --version
# or
python3 --version
```

---

### 5. Network Requirements

Ensure network connectivity between the MCP server and WebLogic Admin Server:

| Port | Protocol | Purpose |
|------|----------|---------|
| 7001 | T3/HTTP | Default Admin Server port |
| 7002 | T3S/HTTPS | Default SSL Admin Server port |
| 9002 | HTTP | Default Admin Channel (if enabled) |

---

## WLST Connection Protocols

WLST supports multiple protocols for connecting to WebLogic Server. Choose the appropriate protocol based on your security requirements.

### Protocol Reference

| Protocol | URL Format | Security | Use Case |
|----------|------------|----------|----------|
| `t3` | `t3://host:port` | None | Development, internal networks |
| `t3s` | `t3s://host:port` | SSL/TLS | Production, secure environments |
| `http` | `http://host:port` | None | Through firewalls (tunneling) |
| `https` | `https://host:port` | SSL/TLS | Through firewalls with SSL |
| `iiop` | `iiop://host:port` | None | CORBA interoperability |
| `iiops` | `iiops://host:port` | SSL/TLS | Secure CORBA |

### T3 Protocol (Default)

Oracle's proprietary protocol optimized for WebLogic communication.

```bash
# Non-secure (development only)
WLST_ADMIN_URL=t3://localhost:7001

# Secure (recommended for production)
WLST_ADMIN_URL=t3s://localhost:7002
```

**Advantages:**
- Best performance
- Full feature support
- Native WebLogic protocol

**Considerations:**
- May be blocked by firewalls
- Requires direct network access

### HTTP/HTTPS Protocol (Tunneling)

HTTP tunneling for environments where T3 is blocked.

```bash
# Non-secure
WLST_ADMIN_URL=http://localhost:7001

# Secure
WLST_ADMIN_URL=https://localhost:7002
```

**Advantages:**
- Works through firewalls and proxies
- Compatible with load balancers

**Considerations:**
- Slightly higher overhead than T3
- Requires HTTP tunneling enabled on server

### Admin Channel

For secure administration in production environments:

```bash
# Using dedicated admin channel
WLST_ADMIN_URL=t3s://localhost:9002
```

**Note:** Admin channel must be configured in WebLogic domain.

---

## Security & Credentials

### Authentication Methods

#### 1. Environment Variables (Recommended for MCP)

```bash
# Linux/macOS
export WLST_ADMIN_URL=t3s://localhost:7002
export WLST_USERNAME=weblogic
export WLST_PASSWORD=your_secure_password

# Windows
set WLST_ADMIN_URL=t3s://localhost:7002
set WLST_USERNAME=weblogic
set WLST_PASSWORD=your_secure_password
```

#### 2. Encrypted Credential Store

For enhanced security, use WebLogic's encrypted credential store:

**Create Credential Store:**

```python
# Using WLST
connect('weblogic', 'password', 't3://localhost:7001')
storeUserConfig('/path/to/userConfig.secure', '/path/to/userKey.secure')
disconnect()
```

**Use Credential Store:**

```python
# Connect using stored credentials
connect(userConfigFile='/path/to/userConfig.secure',
        userKeyFile='/path/to/userKey.secure',
        url='t3://localhost:7001')
```

#### 3. Wallet-Based Authentication (Oracle Wallet)

For enterprise environments with Oracle Wallet:

```bash
# Set wallet location
export WLST_WALLET_PATH=/path/to/wallet
```

### SSL/TLS Configuration

#### Trust Store Configuration

For secure connections (t3s, https), configure the trust store:

```bash
# Linux/macOS
export WLST_TRUST_STORE=/path/to/truststore.jks
export WLST_TRUST_STORE_PASSWORD=truststore_password

# Windows
set WLST_TRUST_STORE=C:\path\to\truststore.jks
set WLST_TRUST_STORE_PASSWORD=truststore_password
```

#### Import Server Certificate

```bash
# Export certificate from WebLogic
keytool -export -alias wls_server -keystore identity.jks -file server.cer

# Import to trust store
keytool -import -alias wls_server -file server.cer -keystore truststore.jks
```

#### Disable Hostname Verification (Development Only)

```bash
# Only for development/testing - NEVER in production
export WLST_SSL_IGNORE_HOSTNAME=true
```

### Credential Security Best Practices

| Practice | Description |
|----------|-------------|
| **Never commit credentials** | Use `.gitignore` to exclude `.env` files |
| **Use encrypted stores** | WebLogic credential store or Oracle Wallet |
| **Rotate passwords** | Regular password rotation policy |
| **Least privilege** | Create dedicated admin users with minimal permissions |
| **Audit logging** | Enable WebLogic audit logging |
| **Network isolation** | Restrict Admin Server access to trusted networks |

### User Permissions

Create a dedicated user with appropriate roles:

| Role | Permissions |
|------|-------------|
| `Admin` | Full administrative access |
| `Operator` | Start/stop servers, deploy apps |
| `Deployer` | Deploy/undeploy applications only |
| `Monitor` | Read-only monitoring access |

**Recommended:** Create a dedicated MCP user with `Operator` role for most operations.

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/wlst-mcp.git
cd wlst-mcp
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file (never commit this file):

```bash
# Connection
WLST_ADMIN_URL=t3s://localhost:7002
WLST_USERNAME=weblogic
WLST_PASSWORD=your_secure_password

# Oracle Home
ORACLE_HOME=/path/to/oracle/middleware/oracle_home
JAVA_HOME=/path/to/jdk

# Optional: SSL Configuration
WLST_TRUST_STORE=/path/to/truststore.jks
WLST_TRUST_STORE_PASSWORD=truststore_password
```

---

## Configuration

### MCP Server Configuration

Create or edit `config.json`:

```json
{
  "server": {
    "host": "localhost",
    "port": 8080
  },
  "weblogic": {
    "admin_url": "t3s://localhost:7002",
    "username": "weblogic",
    "default_timeout": 120,
    "ssl_enabled": true
  },
  "logging": {
    "level": "INFO",
    "file": "wlst-mcp.log"
  }
}
```

### Claude Desktop Integration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

**Linux/macOS:**
```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python",
      "args": ["/path/to/wlst-mcp/server.py"],
      "env": {
        "WLST_ADMIN_URL": "t3s://localhost:7002",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password",
        "ORACLE_HOME": "/path/to/oracle/middleware",
        "JAVA_HOME": "/path/to/jdk"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "wlst-mcp": {
      "command": "python",
      "args": ["C:\\path\\to\\wlst-mcp\\server.py"],
      "env": {
        "WLST_ADMIN_URL": "t3s://localhost:7002",
        "WLST_USERNAME": "weblogic",
        "WLST_PASSWORD": "your_password",
        "ORACLE_HOME": "C:\\Oracle\\Middleware\\Oracle_Home",
        "JAVA_HOME": "C:\\Program Files\\Java\\jdk-11"
      }
    }
  }
}
```

---

## Verification

### 1. Verify Prerequisites

```bash
# Check Java
java -version

# Check WLST
$ORACLE_HOME/oracle_common/common/bin/wlst.sh -v

# Check Python
python --version
```

### 2. Test WebLogic Connectivity

```bash
# Check Admin Console is accessible
curl -k https://localhost:7002/console

# Or for non-SSL
curl http://localhost:7001/console
```

### 3. Test WLST Connection

```bash
# Linux/macOS
$ORACLE_HOME/oracle_common/common/bin/wlst.sh << EOF
connect('weblogic', 'password', 't3://localhost:7001')
domainRuntime()
print('Connected successfully!')
disconnect()
exit()
EOF
```

### 4. Test MCP Server

Use the `wlst_test_connection` tool:

```json
{
  "tool": "wlst_test_connection",
  "params": {
    "admin_url": "t3s://localhost:7002",
    "username": "weblogic",
    "password": "your_password"
  }
}
```

Expected output:
```
Successfully connected to Admin Server "AdminServer" that belongs to domain "your_domain".
```

---

## Troubleshooting

### Connection Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Server not running | Start Admin Server |
| `Connection timed out` | Firewall blocking | Check firewall rules, use HTTP tunneling |
| `Unknown host` | DNS resolution | Use IP address instead of hostname |
| `SSL handshake failed` | Certificate issue | Import certificate to trust store |

### Authentication Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Authentication failed` | Wrong credentials | Verify username/password |
| `Account locked` | Too many failed attempts | Unlock account in WebLogic Console |
| `Not authorized` | Insufficient permissions | Assign appropriate role to user |

### WLST Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `WLST not found` | Missing ORACLE_HOME | Set ORACLE_HOME environment variable |
| `Java not found` | Missing JAVA_HOME | Set JAVA_HOME environment variable |
| `Class not found` | Incomplete installation | Verify WebLogic installation |

### SSL/TLS Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Certificate not trusted` | Missing CA certificate | Import to trust store |
| `Hostname mismatch` | Certificate CN mismatch | Use correct hostname or disable verification (dev only) |
| `Protocol error` | TLS version mismatch | Check server TLS configuration |

---

## Environment Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `WLST_ADMIN_URL` | Yes | WebLogic Admin Server URL |
| `WLST_USERNAME` | Yes | Admin username |
| `WLST_PASSWORD` | Yes | Admin password |
| `ORACLE_HOME` | Yes | Oracle Middleware home directory |
| `JAVA_HOME` | Yes | JDK installation directory |
| `WL_HOME` | No | WebLogic Server home (defaults to $ORACLE_HOME/wlserver) |
| `WLST_TRUST_STORE` | No | Path to SSL trust store |
| `WLST_TRUST_STORE_PASSWORD` | No | Trust store password |
| `WLST_TIMEOUT` | No | Default operation timeout (seconds) |

---

## Support

For issues and feature requests, please open an issue on GitHub.

## References

- [Oracle WebLogic Server Documentation](https://docs.oracle.com/en/middleware/standalone/weblogic-server/)
- [WLST Command Reference](https://docs.oracle.com/en/middleware/standalone/weblogic-server/14.1.1.0/wlstc/)
- [WebLogic Security Guide](https://docs.oracle.com/en/middleware/standalone/weblogic-server/14.1.1.0/secmg/)
