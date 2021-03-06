# -*- coding: utf-8 -*-

from .exceptions import APISpecError, PluginError


_PATH_CORRECTIONS = {
    'operation_id': 'operationId',
    'external_docs': 'externalDocs'
}

def _serialize_operation(operation):
    """Return operation dict, making necessary casing corrections
    to each key.
    """
    return {
        _PATH_CORRECTIONS.get(key, key): val
        for key, val in operation.items()
    }

class Path(object):
    """Represents a Paths object. Stores a single operation for the path.

    https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#pathsObject

    :param str path: The path template, e.g. ``"/pet/{petId}"``
    :param str method: The HTTP method.
    :param dict operation: The operation object, as a `dict`. See
        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operationObject
    """

    def __init__(self, path=None, method=None, operation=None, **kwargs):
        self.path = path
        self.method = method
        self.operation = _serialize_operation(operation or {})

    def to_dict(self):
        if not self.path:
            raise APISpecError('Path template is not specified')
        if not self.method:
            raise APISpecError('Method is not specified')
        return {
            self.path: {
                self.method.lower(): self.operation
            }
        }

    def update(self, path):
        if path.path:
            self.path = path.path
        if path.method:
            self.method = path.method
        self.operation.update(path.operation)


class APISpec(object):
    """Stores metadata that describes a RESTful API using the Swagger 2.0 specification.
    """

    DEFAULT_CONTENT_TYPES = ['application/json']

    def __init__(self, plugins=(), default_content_types=None, *args, **kwargs):
        # Metadata
        self._definitions = {}
        self._paths = {}
        self.default_content_types = default_content_types or self.DEFAULT_CONTENT_TYPES
        # Plugin and helpers
        self._plugins = {}
        self._definition_helpers = []
        self._path_helpers = []

        for plugin_path in plugins:
            self.setup_plugin(plugin_path)

    def to_dict(self):
        return {
            'definitions': self._definitions,
            'paths': self._paths,
        }

    # NOTE: path and method are required, but they have defaults because
    # they may be added by a plugin
    def add_path(self, path=None, method=None, operation=None, **kwargs):
        """Add a new path object to the spec.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#paths-object-
        """
        path_config = {}
        base = Path(path=path, method=method, path_config=path_config, operation=operation)
        # Execute plugins' helpers
        for func in self._path_helpers:
            base.update(func(
                path=path, method=method, operation=operation, **kwargs
            ))

        self._paths.update(base.to_dict())

    def definition(self, name, properties=None, enum=None, **kwargs):
        """Add a new definition to the spec.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject
        """
        ret = {}
        # Execute all helpers from plugins
        for func in self._definition_helpers:
            ret.update(func(name, **kwargs))
        if properties:
            ret['properties'] = properties
        if enum:
            ret['enum'] = enum
        self._definitions[name] = ret

    # PLUGIN INTERFACE

    # adapted from Sphinx
    def setup_plugin(self, path):
        """Import and setup a plugin. No-op if called twice
        for the same plugin.

        :param str name: Import path to the plugin.
        :raise: PluginError if the given plugin is invalid.
        """
        if path in self._plugins:
            return
        try:
            mod = __import__(
                path, globals=None, locals=None, fromlist=('setup', )
            )
        except ImportError:
            raise PluginError(
                'Could not import plugin "{0}"'.format(path)
            )
        if not hasattr(mod, 'setup'):
            raise PluginError('Plugin "{0}" has no setup() function.')
        else:
            mod.setup(self)
        self._plugins[path] = mod
        return None

    def register_definition_helper(self, func):
        """Register a new definition helper. The helper **must** meet the following conditions:

        - Receive the definition `name` as the first argument.
        - Include ``**kwargs`` in its signature.
        - Return a `dict` representation of the definition's Schema object.

        The helper may define any named arguments after the `name` argument.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject

        :param callable func: The definition helper function.
        """
        self._definition_helpers.append(func)

    def register_path_helper(self, func):
        """Register a new path helper. The helper **must** meet the following conditions:

        - Include ``**kwargs`` in signature.
        - Return a `smore.apispec.core.Path` object.

        The helper may define any named arguments in its signature.
        """
        self._path_helpers.append(func)
