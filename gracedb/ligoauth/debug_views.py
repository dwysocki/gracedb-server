"""
Temporary debugging views for Shibboleth authentication
"""
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import get_user


def debug_shib_headers(request):
    """
    Display all relevant Shibboleth headers and authentication state
    """
    output = []
    output.append("=" * 60)
    output.append("SHIBBOLETH DEBUG INFO")
    output.append("=" * 60)
    output.append("")

    # Settings
    output.append("--- SETTINGS ---")
    output.append(f"PROXY_SHIBBOLETH_AUTH: {getattr(settings, 'PROXY_SHIBBOLETH_AUTH', 'NOT SET')}")
    output.append(f"USE_SHIBBOLETH_LOGIN: {getattr(settings, 'USE_SHIBBOLETH_LOGIN', 'NOT SET')}")
    output.append(f"SHIB_USER_HEADER: {getattr(settings, 'SHIB_USER_HEADER', 'NOT SET')}")
    output.append(f"SHIB_GROUPS_HEADER: {getattr(settings, 'SHIB_GROUPS_HEADER', 'NOT SET')}")
    output.append("")

    # User authentication state
    output.append("--- AUTHENTICATION STATE ---")
    output.append(f"User authenticated: {request.user.is_authenticated}")
    output.append(f"Username: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    output.append(f"User ID: {request.user.id if request.user.is_authenticated else 'N/A'}")
    output.append("")

    # Check for Shibboleth headers
    output.append("--- SHIBBOLETH HEADERS ---")
    shib_headers = [
        'HTTP_REMOTE_USER',
        'HTTP_ISMEMBEROF',
        'HTTP_MAIL',
        'HTTP_GIVENNAME',
        'HTTP_SN',
        'REMOTE_USER',  # Sometimes without HTTP_ prefix
        'ISMEMBEROF',
    ]

    for header in shib_headers:
        value = request.META.get(header, 'NOT PRESENT')
        output.append(f"{header}: {value}")
    output.append("")

    # Check for test headers
    output.append("--- TEST HEADERS (for debugging) ---")
    test_headers = [
        'HTTP_X_TEST_HEADER',
        'HTTP_X_TEST_REMOTE_USER',
        'HTTP_X_TEST_CAPTURED_USER',
        'HTTP_X_AUTHENTICATED_USER',
    ]

    for header in test_headers:
        value = request.META.get(header, 'NOT PRESENT')
        output.append(f"{header}: {value}")
    output.append("")

    # Other useful headers
    output.append("--- OTHER HEADERS ---")
    other_headers = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_FORWARDED_PROTO',
        'REMOTE_ADDR',
        'PATH_INFO',
        'REQUEST_METHOD',
    ]

    for header in other_headers:
        value = request.META.get(header, 'NOT PRESENT')
        output.append(f"{header}: {value}")
    output.append("")

    # All META keys that might be relevant
    output.append("--- ALL HTTP_* HEADERS ---")
    http_headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
    for key in sorted(http_headers.keys()):
        output.append(f"{key}: {http_headers[key]}")
    output.append("")

    # All potential Shibboleth attributes (from Apache environment variables)
    output.append("--- ALL POTENTIAL SHIBBOLETH ATTRIBUTES ---")
    output.append("(Searching all request.META for Shibboleth-related keys)")
    shib_patterns = ['shib', 'saml', 'eppn', 'affiliation', 'entitlement',
                     'persistent-id', 'transient-id', 'targeted-id',
                     'displayname', 'commonname', 'surname', 'givenname',
                     'mail', 'telephoneNumber', 'title', 'initials',
                     'description', 'memberof', 'ismemberof', 'eduPerson',
                     'authenticated', 'auth', 'remote-user', 'remote_user',
                     'assertion', 'session', 'identity']

    shib_related = {}
    for key, value in request.META.items():
        # Check if any pattern matches the key (case-insensitive)
        if any(pattern.lower() in key.lower() for pattern in shib_patterns):
            # Truncate long values
            display_value = str(value)
            if len(display_value) > 200:
                display_value = display_value[:200] + "... (truncated)"
            shib_related[key] = display_value

    if shib_related:
        for key in sorted(shib_related.keys()):
            output.append(f"{key}: {shib_related[key]}")
    else:
        output.append("No Shibboleth-related attributes found in request.META")
    output.append("")

    # Show count of all META keys for reference
    output.append("--- SUMMARY ---")
    output.append(f"Total request.META keys: {len(request.META)}")
    output.append(f"HTTP_* headers: {len(http_headers)}")
    output.append(f"Potential Shibboleth attributes: {len(shib_related)}")
    output.append("")

    output.append("=" * 60)

    return HttpResponse('\n'.join(output), content_type='text/plain')
