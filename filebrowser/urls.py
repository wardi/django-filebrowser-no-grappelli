from django.conf import urls

urlpatterns = urls.patterns('',
    
    # filebrowser urls
    urls.url(r'^browse/$', 'filebrowser.views.browse', name="fb_browse"),
    urls.url(r'^mkdir/', 'filebrowser.views.mkdir', name="fb_mkdir"),
    urls.url(r'^upload/', 'filebrowser.views.upload', name="fb_upload"),
    urls.url(r'^rename/$', 'filebrowser.views.rename', name="fb_rename"),
    urls.url(r'^delete/$', 'filebrowser.views.delete', name="fb_delete"),
    urls.url(r'^versions/$', 'filebrowser.views.versions', name="fb_versions"),
    
    urls.url(r'^check_file/$', 'filebrowser.views._check_file', name="fb_check"),
    urls.url(r'^upload_file/$', 'filebrowser.views._upload_file', name="fb_do_upload"),
    
)
