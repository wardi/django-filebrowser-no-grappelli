from django.conf import urls
from filebrowser import views 

urlpatterns = [
    
    # filebrowser urls
    urls.url(r'^browse/$', views.browse, name="fb_browse"),
    urls.url(r'^mkdir/', views.mkdir, name="fb_mkdir"),
    urls.url(r'^upload/', views.upload, name="fb_upload"),
    urls.url(r'^rename/$', views.rename, name="fb_rename"),
    urls.url(r'^delete/$', views.delete, name="fb_delete"),
    urls.url(r'^versions/$', views.versions, name="fb_versions"),
    
    urls.url(r'^check_file/$', views._check_file, name="fb_check"),
    urls.url(r'^upload_file/$', views._upload_file, name="fb_do_upload"),
    
]
