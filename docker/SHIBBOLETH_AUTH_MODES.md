# Shibboleth Authentication Modes

This document explains the two Shibboleth authentication modes available in GraceDB and how to switch between them.

## Authentication Modes

### Traditional Mode (Default)
- Users see a "Login" button on the site
- Clicking login redirects to Shibboleth IdP
- Only `/post-login/` endpoint is protected by Shibboleth
- After authentication, user is logged into Django session
- Good for: Development, testing, sites with optional authentication

### Proxy Auth Mode
- Entire application protected by Shibboleth (except static files)
- Users authenticate automatically before accessing any page
- No login button needed - authentication happens transparently
- All requests carry Shibboleth headers to Django
- Good for: Production deployments behind reverse proxy, high-security environments

---

## Method 1: Environment Variable (Recommended)

The main `docker/apache-config` file supports switching modes via environment variable.

### To Enable Proxy Auth Mode:

**Docker Compose:**
```yaml
services:
  gracedb:
    environment:
      - USE_PROXY_SHIBBOLETH_AUTH=true
    # ... rest of config
```

**Docker Run:**
```bash
docker run -e USE_PROXY_SHIBBOLETH_AUTH=true ...
```

**Docker Env File:**
```bash
# In your .env file
USE_PROXY_SHIBBOLETH_AUTH=true
```

### To Use Traditional Mode:

Either:
- Set `USE_PROXY_SHIBBOLETH_AUTH=false`
- Or don't set the variable at all (defaults to traditional)

---

## Method 2: Separate Config File

Alternatively, you can use the dedicated config files.

### File Options:

1. **`docker/apache-config`** - Default file with environment variable switching
2. **`docker/apache-config-proxy-auth`** - Standalone file for proxy auth mode only

### To Use Separate File:

**Option A: Mount different config in Docker Compose:**
```yaml
services:
  gracedb:
    volumes:
      # For proxy auth mode:
      - ./docker/apache-config-proxy-auth:/etc/apache2/sites-available/000-default.conf

      # For traditional mode:
      # - ./docker/apache-config:/etc/apache2/sites-available/000-default.conf
```

**Option B: Copy file during build:**
Modify your Dockerfile to copy the appropriate config:
```dockerfile
# For proxy auth mode:
COPY docker/apache-config-proxy-auth /etc/apache2/sites-available/000-default.conf

# For traditional mode:
# COPY docker/apache-config /etc/apache2/sites-available/000-default.conf
```

---

## Django Middleware Configuration

For proxy auth mode to work properly, you also need to update the Django middleware.

### Current Middleware Behavior:
- Only processes headers at `/post-login/` URL
- Suitable for traditional mode

### Proxy Auth Mode Requirements:
- Must process headers on ALL requests (except static files)
- Automatically log in users when `REMOTE_USER` header is present

### Required Change:

Edit `gracedb/ligoauth/middleware.py` around line 32-42:

**Current (Traditional Mode):**
```python
active_url = reverse_lazy('post-login')

def process_request(self, request):
    # This middleware should *only* be active at the post-login URL
    # where shibboleth is also active.
    if not (request.path == self.active_url):
        return
```

**Updated (Proxy Auth Mode):**
```python
# URLs where authentication should NOT be processed
excluded_paths = ['/static/', '/robots.txt', '/documentation/']

def process_request(self, request):
    # Skip authentication for static files and public resources
    if any(request.path.startswith(path) for path in self.excluded_paths):
        return
```

**Optional: Make middleware mode-aware:**
```python
def __init__(self, get_response):
    self.get_response = get_response
    self.proxy_mode = getattr(settings, 'PROXY_SHIBBOLETH_AUTH', False)
    if self.proxy_mode:
        self.excluded_paths = ['/static/', '/robots.txt', '/documentation/']
    else:
        self.active_url = reverse_lazy('post-login')

def process_request(self, request):
    if self.proxy_mode:
        # Proxy mode: process all requests except excluded paths
        if any(request.path.startswith(path) for path in self.excluded_paths):
            return
    else:
        # Traditional mode: only process at post-login URL
        if not (request.path == self.active_url):
            return

    # ... rest of authentication logic ...
```

Then in `config/settings/base.py`:
```python
# Set to True to enable proxy authentication mode
PROXY_SHIBBOLETH_AUTH = os.environ.get('USE_PROXY_SHIBBOLETH_AUTH', 'false').lower() == 'true'
```

---

## What Gets Protected/Unprotected

### Protected by Shibboleth (in Proxy Auth Mode):
- All application URLs (`/`, `/api/`, `/events/`, etc.)
- Admin pages (`/admin/`)
- User pages

### NOT Protected (accessible without auth):
- Static files (`/static/`)
- Documentation (`/documentation/`)
- Robots.txt (`/robots.txt`)
- Shibboleth endpoints (`/Shibboleth.sso/`, `/shibboleth-ds/`, `/shibboleth-sp/`)

### Special Cases:
- `/admin_docs/` - Still protected by user whitelist (see apache-config line 154-159)

---

## Headers Passed to Django

In both modes, these headers are passed from Shibboleth to Django:

| Header | Description | Django Setting |
|--------|-------------|----------------|
| `REMOTE_USER` | Username | `SHIB_USER_HEADER` |
| `ISMEMBEROF` | Group memberships (semicolon-delimited) | `SHIB_GROUPS_HEADER` |
| `MAIL` | Email address | `SHIB_ATTRIBUTE_MAP['email']` |
| `GIVENNAME` | First name | `SHIB_ATTRIBUTE_MAP['first_name']` |
| `SN` | Last name | `SHIB_ATTRIBUTE_MAP['last_name']` |

**Difference:**
- **Traditional mode:** Headers only set for `/post-login/` requests
- **Proxy mode:** Headers set for ALL protected requests

---

## Testing

### Test Traditional Mode:
1. Access site → should see login button
2. Click login → redirected to Shibboleth IdP
3. Authenticate → redirected back, logged in
4. Static files load without authentication

### Test Proxy Auth Mode:
1. Access any page (e.g., `/`, `/events/`) → immediately redirected to Shibboleth IdP
2. Authenticate → redirected back to requested page, already logged in
3. No login button visible (user automatically authenticated)
4. Static files still load without authentication
5. Logout works, re-authentication required on next request

---

## Troubleshooting

### Apache not recognizing environment variable:
- Make sure environment variable is set BEFORE Apache starts
- Check with: `docker exec <container> env | grep USE_PROXY_SHIBBOLETH_AUTH`
- Restart container after setting variable

### Headers not reaching Django:
- Check Apache error logs: `docker logs <container> 2>&1 | grep -i shib`
- Verify `ShibUseHeaders On` is set
- Check Django receives headers: Add debug logging in middleware

### Infinite redirect loop:
- Usually means Shibboleth session not being created
- Check `/Shibboleth.sso/Session` endpoint
- Verify Shibboleth SP metadata is registered with IdP

### Static files requiring authentication:
- Check LocationMatch regex excludes static paths
- Verify ProxyPass excludes static files
- Check browser network tab for authentication redirects on static resources

---

## Quick Reference

| Task | Command/Config |
|------|----------------|
| Enable proxy auth | Set `USE_PROXY_SHIBBOLETH_AUTH=true` |
| Use traditional auth | Set `USE_PROXY_SHIBBOLETH_AUTH=false` or leave unset |
| Check current mode | `docker exec <container> env \| grep USE_PROXY_SHIBBOLETH_AUTH` |
| View Shibboleth session | Browse to `/Shibboleth.sso/Session` |
| View Shibboleth status | Browse to `/Shibboleth.sso/Status` |
| Apache config location | `/etc/apache2/sites-available/000-default.conf` |
| Restart Apache | `docker exec <container> apache2ctl graceful` |
