from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from filebrowser.views import upload

__author__ = 'pahaz'

from django.contrib import admin
from django.conf.urls.defaults import patterns,url
from django.utils.functional import update_wrapper
from django.contrib.admin.sites import AdminSite

from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect, HttpResponseForbidden , HttpResponse

from filebrowser.models import FFile

class TemplatesAdmin(admin.ModelAdmin):
    """
        Admin for TemplatesAdmin
    """
    model = FFile

    def changelist_view(self, request ):
        return redirect(reverse('fb_browse'))

    def add_view(self, request, form_url='', extra_content=None):
        return redirect(reverse('fb_browse'))

    def delete_view(self, request, object_id, extra_context=None ):
        return redirect(reverse('fb_browse'))

    def history_view(self, request, object_id , extra_context=None):
        return redirect(reverse('fb_browse'))

    def change_view(self, request, object_id, extra_context=None):
        return redirect(reverse('fb_browse'))


admin.site.register(FFile, TemplatesAdmin)
