"""
Define the custom Exceptions for Eventgen.
"""



class PluginNotLoaded(Exception):

    def __init__(self, bindir, libdir, plugindir, name, type, msg="Plugin Not Loaded, attempting to load."):
        """Exception raised when a sample asks for a plugin that is not in the plugin list.
        This exception triggers an upload reload of plugins that expands the search path of plugins to add.

        :param msg: The message
        :param bindir: a bindir to check for plugins
        :param libdir: The libdir to check in for plugins
        :param plugindir: The lib/plugin/<type> dir of plugins
        :param name: The name of the plugin
        :param type: The type of plugin
        """
        self.msg = msg
        self.bindir = bindir
        self.libdir = libdir
        self.plugindir = plugindir
        self.name = name
        self.type = type
        super(PluginNotLoaded, self).__init__(msg)

class FailedLoadingPlugin(Exception):

    def __init__(self, name, msg="Plugin Not Found or Failed to load."):
        """Exception raised when a sample asks for a plugin that can't be found

        :param msg: The message
        :param name: The name of the plugin
        """
        self.msg = msg
        self.name = name
        super(FailedLoadingPlugin, self).__init__(msg)
