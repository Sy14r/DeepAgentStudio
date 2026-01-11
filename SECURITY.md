# Security Considerations

This document outlines security considerations for deploying DeepAgentStudio.

## Deployment Modes

### Self-Hosted (Trusted Users)

For deployments where all users are trusted (e.g., internal team use, personal projects):

- Default configuration is acceptable
- Custom tools can be enabled
- All features available

### Multi-Tenant (Untrusted Users)

For deployments with untrusted users, additional precautions are required:

1. **Disable custom Python tools** - Only allow built-in tools
2. **Restrict MCP server creation** - Or use admin-only access
3. **Deploy in isolated environment** - Containers, VMs, or separate infrastructure
4. **Implement rate limiting** - At reverse proxy layer (nginx, Cloudflare, etc.)

---

## Security Features

### Authentication

- **JWT tokens** with 30-minute expiration
- **bcrypt** password hashing (12+ character minimum)
- **Bearer token** authentication for API endpoints

### Data Encryption

- **API keys** encrypted at rest using Fernet symmetric encryption
- **Environment variables** for MCP servers encrypted
- **Secrets** never returned in API responses

### Authorization

- **User ownership** enforced on all resources
- **Built-in vs custom** separation (built-in items read-only)
- **Cascade deletion** when users are removed

---

## Known Limitations

### Custom Tool Code Execution

**Risk Level: HIGH for untrusted users**

Custom Python tools execute with full access to:
- File system
- Network
- Environment variables
- All Python modules

**Mitigations:**
- Only allow trusted users to create custom tools
- Use only built-in tools for untrusted deployments
- Deploy in isolated containers if custom tools needed

### MCP Server Commands

**Risk Level: MEDIUM (mitigated)**

MCP stdio servers execute subprocess commands. Commands are restricted to a whitelist:
- `npx`, `uvx`, `pipx` (package runners)
- `node`, `python`, `python3` (interpreters)
- `docker`, `podman` (container runners)

### Web Request Tools

**Risk Level: MEDIUM**

Web fetch and HTTP request tools can access:
- Internal network addresses
- Cloud metadata endpoints
- Any URL the server can reach

**Mitigations:**
- Deploy with network segmentation
- Use firewall rules to block internal access from containers
- Consider disabling web tools for untrusted users

---

## Environment Variables

Required secrets (generate secure random values):

```bash
# JWT signing key (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-secure-random-key-here

# Encryption key for API keys (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-fernet-key-here

# Database password
POSTGRES_PASSWORD=your-secure-password-here
```

**Important:** Never commit real secrets to version control.

---

## Recommended Production Setup

1. **Reverse Proxy** (nginx, Traefik, Caddy)
   - TLS termination
   - Rate limiting:
     - Login endpoint: 5 requests/minute per IP
     - Registration: 3 requests/hour per IP
     - API endpoints: 100 requests/minute per user
   - Request size limits (recommended: 10MB max)

2. **Network Isolation**
   - Backend in private network
   - Only expose frontend/API through proxy
   - Database not publicly accessible

3. **Container Security**
   - Run as non-root user
   - Read-only file systems where possible
   - Resource limits (CPU, memory)

4. **Monitoring**
   - Log all authentication events
   - Monitor for unusual patterns
   - Alert on repeated failures

---

## Reporting Security Issues

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue
2. Email security concerns privately
3. Include steps to reproduce
4. Allow time for a fix before disclosure

---

## Security Checklist for Deployment

- [ ] Generated unique `JWT_SECRET_KEY`
- [ ] Generated unique `ENCRYPTION_KEY`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configured `CORS_ORIGINS` appropriately
- [ ] Deployed behind reverse proxy with TLS
- [ ] Rate limiting enabled at proxy layer
- [ ] Database not publicly accessible
- [ ] Reviewed user access requirements
- [ ] Decided on custom tool policy
- [ ] Configured appropriate resource limits
