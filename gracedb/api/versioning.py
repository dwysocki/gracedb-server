import logging

from rest_framework import versioning

# Set up logger
logger = logging.getLogger(__name__)


class NestedNamespaceVersioning(versioning.NamespaceVersioning):
    version_nest_level = 2 # starts with 1

    def reverse(self, viewname, args=None, kwargs=None, request=None,
        format=None, **extra):
        if request.version is not None:
            viewname = self.get_versioned_viewname(viewname, request)
        return super(NestedNamespaceVersioning, self).reverse(
            viewname, args, kwargs, request, format, **extra
        )

    def get_versioned_viewname(self, viewname, request=None):
        # Split up viewname parts
        viewname_parts = viewname.split(':')
        namespaces = viewname_parts[:-1]
        viewname_only = viewname_parts[-1]

        # Get version
        if request and request.version:
            version = request.version
        else:
            # The 'default_version' attribute is set by the BaseVersioning
            # class
            version = self.default_version

        # Add version into namespaces
        if version not in namespaces:
            namespaces.insert(self.version_nest_level - 1, version)

        versioned_viewname = ':'.join(namespaces + [viewname_only])
        return versioned_viewname

