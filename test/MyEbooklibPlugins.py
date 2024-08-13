from ebooklib.plugins.base import BasePlugin
class doNothingBeforeWirteEpub(BasePlugin):
    NAME = 'doNothingBeforeWirteEpub'

    def before_write(self, book):
        """Processing before save"""
        return False

    def after_write(self, book):
        """Processing after save"""
        return False

    # def before_read(self, book):
    #     """Processing before save"""
    #     return True
    #
    # def after_read(self, book):
    #     """Processing after save"""
    #     return True

    # def item_after_read(self, book, item):
    #     """Process general item after read."""
    #     return True

    def item_before_write(self, book, item):
        """Process general item before write."""
        return False

    # def html_after_read(self, book, chapter):
    #     """Processing HTML before read."""
    #     return True

    def html_before_write(self, book, chapter):
        """Processing HTML before save."""
        return False
