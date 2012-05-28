# coding: utf-8

# general imports
import os, re
from time import gmtime, strftime

# django imports
from django.shortcuts import render_to_response, HttpResponse
from django.template import RequestContext as Context
from django.http import HttpResponseRedirect, Http404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from django.utils.translation import ugettext as _
from django.conf import settings
from django import forms
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import Signal
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.utils.encoding import smart_str

try:
    # django SVN
    from django.views.decorators.csrf import csrf_exempt
except:
    # django 1.1
    from django.contrib.csrf.middleware import csrf_exempt

from django.contrib import messages

# filebrowser imports
from filebrowser.settings import *
from filebrowser.conf import fb_settings
from filebrowser.functions import path_to_url, sort_by_attr, get_path, get_file, get_version_path, get_breadcrumbs, get_filterdate, get_settings_var, handle_file_upload, convert_filename
from filebrowser.templatetags.fb_tags import query_helper
from filebrowser.base import FileObject
from filebrowser.decorators import flash_login_required

# Precompile regular expressions
filter_re = []
for exp in EXCLUDE:
   filter_re.append(re.compile(exp))
for k,v in VERSIONS.iteritems():
    exp = (r'_%s.(%s)') % (k, '|'.join(EXTENSION_LIST))
    filter_re.append(re.compile(exp))

# pahaz security
from filebrowser.settings import FOLDER_REGEX
alnum_name_re = re.compile(FOLDER_REGEX)

ROOT_DIR = os.path.abspath(os.path.join(fb_settings.MEDIA_ROOT, fb_settings.DIRECTORY))
def _check_access(*path):
    abs_path = os.path.abspath(os.path.join(ROOT_DIR, *path))
    if not abs_path.startswith(ROOT_DIR):
        msg = _('Access Denited.')
        messages.warning(request,message=msg)
        raise ImproperlyConfigured, _("Error Access Denited. Maybe you want hack me?")
    return abs_path
    
def _check_name(name):
    name = os.path.basename(name)
    search = alnum_name_re.search(name)
    if not search:
        msg = _('Invalid name.')
        messages.warning(request,message=msg)
        raise ImproperlyConfigured, _("Name strange. Maybe you want hack me?")
    return search.group(0)

def browse(request):
    """
    Browse Files/Directories.
    """
    # QUERY / PATH CHECK
    query = request.GET.copy()
    path = get_path(query.get('dir', ''))
    directory = get_path('')
    filter_date = request.GET.get('filter_date')
    filter_type = request.GET.get('filter_type')
    q = request.GET.get('q')
    _type = query.get('type')
    
    if path is None:
        msg = _('The requested Folder does not exist.')
        messages.warning(request,message=msg)
        if directory is None:
            # The DIRECTORY does not exist, raise an error to prevent eternal redirecting.
            raise ImproperlyConfigured, _("Error finding Upload-Folder. Maybe it does not exist?")
        redirect_url = reverse("fb_browse") + query_helper(query, "", "dir")
        return HttpResponseRedirect(redirect_url)
        
    abs_path = _check_access(path)
    
    # INITIAL VARIABLES
    results_var = {'results_total': 0, 'results_current': 0, 'delete_total': 0, 'images_total': 0, 'select_total': 0 }
    counter = {}
    for k,v in EXTENSIONS.iteritems():
        counter[k] = 0
    
    dir_list = os.listdir(abs_path)
    files = []
    for file in dir_list:
        
        # EXCLUDE FILES MATCHING VERSIONS_PREFIX OR ANY OF THE EXCLUDE PATTERNS
        filtered = file.startswith('.')
        for re_prefix in filter_re:
            if re_prefix.search(file):
                filtered = True
        if filtered:
            continue
        results_var['results_total'] += 1
        
        # CREATE FILEOBJECT
        fileobject = FileObject(os.path.join(abs_path, file))
        
        # FILTER / SEARCH
        append = False
        if fileobject.filetype == (filter_type if filter_type else fileobject.filetype) and get_filterdate(filter_date, fileobject.date):
            append = True
        if q and not re.compile(q.lower(), re.M).search(file.lower()):
            append = False
        
        # APPEND FILE_LIST
        if append:
            try:
                # COUNTER/RESULTS
                if fileobject.filetype == 'Image':
                    results_var['images_total'] += 1
                if fileobject.filetype != 'Folder':
                    results_var['delete_total'] += 1
                elif fileobject.filetype == 'Folder' and fileobject.is_empty:
                    results_var['delete_total'] += 1
                if _type and _type in SELECT_FORMATS and fileobject.filetype in SELECT_FORMATS[_type]:
                    results_var['select_total'] += 1
                elif not _type:
                    results_var['select_total'] += 1
            except OSError:
                # Ignore items that have problems
                continue
            else:
                files.append(fileobject)
                results_var['results_current'] += 1
        
        # COUNTER/RESULTS
        if fileobject.filetype:
            counter[fileobject.filetype] += 1
    
    # SORTING
    query['o'] = request.GET.get('o', DEFAULT_SORTING_BY)
    query['ot'] = request.GET.get('ot', DEFAULT_SORTING_ORDER)
    files = sort_by_attr(files, request.GET.get('o', DEFAULT_SORTING_BY))
    if not request.GET.get('ot') and DEFAULT_SORTING_ORDER == "desc" or request.GET.get('ot') == "desc":
        files.reverse()
    
    p = Paginator(files, LIST_PER_PAGE)
    try:
        page_nr = request.GET.get('p', '1')
    except:
        page_nr = 1
    try:
        page = p.page(page_nr)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)
    
    return render_to_response('filebrowser/index.html', {
        'dir': path,
        'p': p,
        'page': page,
        'results_var': results_var,
        'counter': counter,
        'query': query,
        'title': _(u'FileBrowser'),
        'settings_var': get_settings_var(),
        'breadcrumbs': get_breadcrumbs(query, path),
        'breadcrumbs_title': ""
    }, context_instance=Context(request))
browse = staff_member_required(never_cache(browse))


# mkdir signals
filebrowser_pre_createdir = Signal(providing_args=["path", "dirname"])
filebrowser_post_createdir = Signal(providing_args=["path", "dirname"])

def mkdir(request):
    """
    Make Directory.
    """
    
    from filebrowser.forms import MakeDirForm
    
    # QUERY / PATH CHECK
    query = request.GET
    path = get_path(query.get('dir', ''))
    
    if path is None:
        msg = _('The requested Folder does not exist.')
        messages.warning(request,message=msg)
        return HttpResponseRedirect(reverse("fb_browse"))
        
    abs_path = _check_access(path)
    
    if request.method == 'POST':
        form = MakeDirForm(abs_path, request.POST)
        if form.is_valid():
            dir_name = form.cleaned_data['dir_name'] # dir_name secutity dy RegExp
            server_path = os.path.join(abs_path, dir_name) 
            try:
                # PRE CREATE SIGNAL
                filebrowser_pre_createdir.send(sender=request, path=abs_path, dirname=dir_name)
                # CREATE FOLDER
                os.mkdir(server_path)
                os.chmod(server_path, 0775)
                # POST CREATE SIGNAL
                filebrowser_post_createdir.send(sender=request, path=abs_path, dirname=dir_name)
                # MESSAGE & REDIRECT
                msg = _('The Folder %s was successfully created.') % (dir_name, )
                messages.success(request,message=msg)
                # on redirect, sort by date desc to see the new directory on top of the list
                # remove filter in order to actually _see_ the new folder
                # remove pagination
                redirect_url = reverse("fb_browse") + query_helper(query, "ot=desc,o=date", "ot,o,filter_type,filter_date,q,p")
                return HttpResponseRedirect(redirect_url)
            except OSError, (errno, strerror):
                if errno == 13:
                    form.errors['dir_name'] = forms.util.ErrorList([_('Permission denied.')])
                else:
                    form.errors['dir_name'] = forms.util.ErrorList([_('Error creating folder.')])
    else:
        form = MakeDirForm(abs_path)
    
    return render_to_response('filebrowser/makedir.html', {
        'form': form,
        'query': query,
        'title': _(u'New Folder'),
        'settings_var': get_settings_var(),
        'breadcrumbs': get_breadcrumbs(query, path),
        'breadcrumbs_title': _(u'New Folder')
    }, context_instance=Context(request))
mkdir = staff_member_required(never_cache(mkdir))


def upload(request):
    """
    Multipe File Upload.
    """
    
    from django.http import parse_cookie
    
    # QUERY / PATH CHECK
    query = request.GET
    path = get_path(query.get('dir', ''))
    if path is None:
        msg = _('The requested Folder does not exist.')
        messages.warning(request,message=msg)
        return HttpResponseRedirect(reverse("fb_browse"))
        
    abs_path = _check_access(path)
    
    # SESSION (used for flash-uploading)
    cookie_dict = parse_cookie(request.META.get('HTTP_COOKIE', ''))
    engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
    session_key = cookie_dict.get(settings.SESSION_COOKIE_NAME, None)
    
    return render_to_response('filebrowser/upload.html', {
        'query': query,
        'title': _(u'Select files to upload'),
        'settings_var': get_settings_var(),
        'session_key': session_key,
        'breadcrumbs': get_breadcrumbs(query, path),
        'breadcrumbs_title': _(u'Upload')
    }, context_instance=Context(request))
upload = staff_member_required(never_cache(upload))


@csrf_exempt
def _check_file(request):
    """
    Check if file already exists on the server.
    """
    
    from django.utils import simplejson
    
    folder = _check_name(request.POST.get('folder'))
    fb_uploadurl_re = re.compile(r'^.*(%s)' % reverse("fb_upload"))
    folder = fb_uploadurl_re.sub('', folder)
    
    fileArray = {}
    if request.method == 'POST':
        for k,v in request.POST.items():
            if k != "folder":
                v = convert_filename(v)
                if os.path.isfile(smart_str(_check_access(folder, v))):
                    fileArray[k] = v
    
    return HttpResponse(simplejson.dumps(fileArray))


# upload signals
filebrowser_pre_upload = Signal(providing_args=["path", "file"])
filebrowser_post_upload = Signal(providing_args=["path", "file"])

@csrf_exempt
@flash_login_required
def _upload_file(request):
    """
    Upload file to the server.
    """
    
    from django.core.files.move import file_move_safe
    
    if request.method == 'POST':
        folder = _check_name(request.POST.get('folder'))
        fb_uploadurl_re = re.compile(r'^.*(%s)' % reverse("fb_upload"))
        folder = fb_uploadurl_re.sub('', folder)
        abs_path = _check_access(folder)
        if request.FILES:
            filedata = request.FILES['Filedata']
            filedata.name = convert_filename(_check_name(filedata.name))
            # PRE UPLOAD SIGNAL
            filebrowser_pre_upload.send(sender=request, path=folder, file=filedata)
            # HANDLE UPLOAD
            uploadedfile = handle_file_upload(abs_path, filedata)
            # MOVE UPLOADED FILE
            # if file already exists
            fn = smart_str(_check_access(folder, filedata.name))
            if os.path.isfile(fn):
                old_file = smart_str(os.path.join(abs_path, filedata.name))
                new_file = smart_str(os.path.join(abs_path, uploadedfile))
                file_move_safe(new_file, old_file)
            # POST UPLOAD SIGNAL
            filebrowser_post_upload.send(sender=request, path=folder, file=FileObject(fn))
    return HttpResponse('True')
#_upload_file = flash_login_required(_upload_file)


# delete signals
filebrowser_pre_delete = Signal(providing_args=["path", "filename"])
filebrowser_post_delete = Signal(providing_args=["path", "filename"])

def delete(request):
    """
    Delete existing File/Directory.
    
    When trying to delete a Directory, the Directory has to be empty.
    """
    
    # QUERY / PATH CHECK
    query = request.GET
    path = get_path(_check_name(query.get('dir', '')))
    filename = get_file(query.get('dir', ''), _check_name(query.get('filename', '')))
    if path is None or filename is None:
        if path is None:
            msg = _('The requested Folder does not exist.')
        else:
            msg = _('The requested File does not exist.')
        messages.warning(request,message=msg)
        return HttpResponseRedirect(reverse("fb_browse"))
        
    abs_path = _check_access(path)
    
    msg = ""
    if request.GET:
        if request.GET.get('filetype') != "Folder":
            relative_server_path = os.path.join(fb_settings.DIRECTORY, path, filename)
            try:
                # PRE DELETE SIGNAL
                filebrowser_pre_delete.send(sender=request, path=path, filename=filename)
                # DELETE IMAGE VERSIONS/THUMBNAILS
                for version in VERSIONS:
                    try:
                        os.unlink(os.path.join(fb_settings.MEDIA_ROOT, get_version_path(relative_server_path, version)))
                    except:
                        pass
                # DELETE FILE
                os.unlink(smart_str(os.path.join(abs_path, filename)))
                # POST DELETE SIGNAL
                filebrowser_post_delete.send(sender=request, path=path, filename=filename)
                # MESSAGE & REDIRECT
                msg = _('The file %s was successfully deleted.') % (filename.lower())
                messages.success(request,message=msg)
                redirect_url = reverse("fb_browse") + query_helper(query, "", "filename,filetype")
                return HttpResponseRedirect(redirect_url)
            except OSError:
                # todo: define error message
                msg = OSError
        else:
            try:
                # PRE DELETE SIGNAL
                filebrowser_pre_delete.send(sender=request, path=path, filename=filename)
                # DELETE FOLDER
                os.rmdir(os.path.join(abs_path, filename))
                # POST DELETE SIGNAL
                filebrowser_post_delete.send(sender=request, path=path, filename=filename)
                # MESSAGE & REDIRECT
                msg = _('The folder %s was successfully deleted.') % (filename.lower())
                messages.success(request,message=msg)
                redirect_url = reverse("fb_browse") + query_helper(query, "", "filename,filetype")
                return HttpResponseRedirect(redirect_url)
            except OSError:
                # todo: define error message
                msg = OSError
    
    if msg:
        request.user.message_set.create(message=msg)
    
    return render_to_response('filebrowser/index.html', {
        'dir': dir_name,
        'file': request.GET.get('filename', ''),
        'query': query,
        'settings_var': get_settings_var(),
        'breadcrumbs': get_breadcrumbs(query, dir_name),
        'breadcrumbs_title': ""
    }, context_instance=Context(request))
delete = staff_member_required(never_cache(delete))


# rename signals
filebrowser_pre_rename = Signal(providing_args=["path", "filename", "new_filename"])
filebrowser_post_rename = Signal(providing_args=["path", "filename", "new_filename"])

def rename(request):
    """
    Rename existing File/Directory.
    
    Includes renaming existing Image Versions/Thumbnails.
    """
    
    from filebrowser.forms import RenameForm
    
    # QUERY / PATH CHECK
    query = request.GET
    path = get_path(query.get('dir', ''))
    filename = get_file(query.get('dir', ''), _check_name(query.get('filename', '')))
    if path is None or filename is None:
        if path is None:
            msg = _('The requested Folder does not exist.')
        else:
            msg = _('The requested File does not exist.')
        messages.warning(request,message=msg)
        return HttpResponseRedirect(reverse("fb_browse"))
    abs_path = _check_access(path)
    file_extension = os.path.splitext(filename)[1].lower()
    
    if request.method == 'POST':
        form = RenameForm(abs_path, file_extension, request.POST)
        if form.is_valid():
            relative_server_path = os.path.join(fb_settings.DIRECTORY, path, filename)
            new_filename = form.cleaned_data['name'] + file_extension
            new_relative_server_path = os.path.join(fb_settings.DIRECTORY, path, new_filename)
            try:
                # PRE RENAME SIGNAL
                filebrowser_pre_rename.send(sender=request, path=path, filename=filename, new_filename=new_filename)
                # DELETE IMAGE VERSIONS/THUMBNAILS
                # regenerating versions/thumbs will be done automatically
                for version in VERSIONS:
                    try:
                        os.unlink(os.path.join(fb_settings.MEDIA_ROOT, get_version_path(relative_server_path, version)))
                    except:
                        pass
                # RENAME ORIGINAL
                os.rename(os.path.join(fb_settings.MEDIA_ROOT, relative_server_path), os.path.join(fb_settings.MEDIA_ROOT, new_relative_server_path))
                # POST RENAME SIGNAL
                filebrowser_post_rename.send(sender=request, path=path, filename=filename, new_filename=new_filename)
                # MESSAGE & REDIRECT
                msg = _('Renaming was successful.')
                messages.success(request,message=msg)
                redirect_url = reverse("fb_browse") + query_helper(query, "", "filename")
                return HttpResponseRedirect(redirect_url)
            except OSError, (errno, strerror):
                form.errors['name'] = forms.util.ErrorList([_('Error.')])
    else:
        form = RenameForm(abs_path, file_extension)
    
    return render_to_response('filebrowser/rename.html', {
        'form': form,
        'query': query,
        'file_extension': file_extension,
        'title': _(u'Rename "%s"') % filename,
        'settings_var': get_settings_var(),
        'breadcrumbs': get_breadcrumbs(query, path),
        'breadcrumbs_title': _(u'Rename')
    }, context_instance=Context(request))
rename = staff_member_required(never_cache(rename))


def versions(request):
    """
    Show all Versions for an Image according to ADMIN_VERSIONS.
    """
    
    # QUERY / PATH CHECK
    query = request.GET
    path = get_path(query.get('dir', ''))
    filename = get_file(query.get('dir', ''), _check_name(query.get('filename', '')))
    if path is None or filename is None:
        if path is None:
            msg = _('The requested Folder does not exist.')
        else:
            msg = _('The requested File does not exist.')
        messages.warning(request,message=msg)
        return HttpResponseRedirect(reverse("fb_browse"))
    abs_path = _check_access(path)
    
    return render_to_response('filebrowser/versions.html', {
        'original': path_to_url(os.path.join(fb_settings.DIRECTORY, path, filename)),
        'query': query,
        'title': _(u'Versions for "%s"') % filename,
        'settings_var': get_settings_var(),
        'breadcrumbs': get_breadcrumbs(query, path),
        'breadcrumbs_title': _(u'Versions for "%s"') % filename
    }, context_instance=Context(request))
versions = staff_member_required(never_cache(versions))


