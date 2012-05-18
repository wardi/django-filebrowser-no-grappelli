
from filebrowser import settings

class FileBrowserSettings(object):
    """
    Proxy for file browser settings defined at module level

    This class allows for the addition of properties to
    compute the correct setting, and makes accessing settings
    explicit in modules that use it:

    >>> from filebrowser.conf import fb_settings
    >>> fb_settings.MEDIA_ROOT # etc..
    """
    def __getattr__(self, name):
        return getattr(settings, name)

fb_settings = FileBrowserSettings()
