__author__ = 'pahaz'

from django.db import models
from django.core.exceptions import SuspiciousOperation
from django.utils.translation import ugettext as _

class FFile(models.Model):
    """
        Faking a model to use filebrowse in
        admin site (without other hacks). I hack here
        to avoid the user to hack forward. 

        The name FFile avoid ugly-url (FakedFileModel)
    """
    class Meta:
        verbose_name , verbose_name_plural = _("File") , _("Files")
        managed = False

    def save(self, *args, **kwargs):
        raise SuspiciousOperation("filebrowser model is faked. Sorry to disappoint you...")

    def delete(self, *args, **kwargs):
        raise SuspiciousOperation("filebrowser model is faked. Sorry to disappoint you...")
