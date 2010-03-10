# coding: utf-8

# imports
import re, os

# django imports
from django import forms
from django.forms.formsets import BaseFormSet
from django.utils.translation import ugettext as _

# filebrowser imports
from filebrowser.settings import MAX_UPLOAD_SIZE
from filebrowser.functions import convert_filename, get_file_type

alnum_name_re = re.compile(r'^[\sa-zA-Z0-9._/-]+$')


class MakeDirForm(forms.Form):
    """
    Form for creating Folder.
    """
    
    def __init__(self, path, *args, **kwargs):
        self.path = path
        super(MakeDirForm, self).__init__(*args, **kwargs)
        
    dir_name = forms.CharField(widget=forms.TextInput(attrs=dict({ 'class': 'vTextField' }, max_length=50, min_length=3)), label=_(u'Name'), help_text=_(u'Only letters, numbers, underscores, spaces and hyphens are allowed.'), required=True)
    
    def clean_dir_name(self):
        if self.cleaned_data['dir_name']:
            # only letters, numbers, underscores, spaces and hyphens are allowed.
            if not alnum_name_re.search(self.cleaned_data['dir_name']):
                raise forms.ValidationError(_(u'Only letters, numbers, underscores, spaces and hyphens are allowed.'))
            # Folder must not already exist.
            if os.path.isdir(os.path.join(self.path, convert_filename(self.cleaned_data['dir_name']))):
                raise forms.ValidationError(_(u'The Folder already exists.'))
        return convert_filename(self.cleaned_data['dir_name'])


class RenameForm(forms.Form):
    """
    Form for renaming Folder/File.
    """
    
    def __init__(self, path, file_extension, *args, **kwargs):
        self.path = path
        self.file_extension = file_extension
        super(RenameForm, self).__init__(*args, **kwargs)
    
    name = forms.CharField(widget=forms.TextInput(attrs=dict({ 'class': 'vTextField' }, max_length=50, min_length=3)), label=_(u'New Name'), help_text=_('Only letters, numbers, underscores, spaces and hyphens are allowed.'), required=True)
    
    def clean_name(self):
        if self.cleaned_data['name']:
            # only letters, numbers, underscores, spaces and hyphens are allowed.
            if not alnum_name_re.search(self.cleaned_data['name']):
                raise forms.ValidationError(_(u'Only letters, numbers, underscores, spaces and hyphens are allowed.'))
            #  folder/file must not already exist.
            if os.path.isdir(os.path.join(self.path, convert_filename(self.cleaned_data['name']))):
                raise forms.ValidationError(_(u'The Folder already exists.'))
            elif os.path.isfile(os.path.join(self.path, convert_filename(self.cleaned_data['name']) + self.file_extension)):
                raise forms.ValidationError(_(u'The File already exists.'))
        return convert_filename(self.cleaned_data['name'])


class BaseUploadFormSet(BaseFormSet):

    # this is just for passing the parameters (path_server, path) to the uploadform.
    # overly complicated, but necessary for the clean-methods in UploadForm.
    
    def __init__(self, **kwargs):
        self.path = kwargs['path']
        del kwargs['path']
        super(BaseUploadFormSet, self).__init__(**kwargs)
    
    def _construct_form(self, i, **kwargs):
        # this works because BaseFormSet._construct_form() passes **kwargs
        # to the form's __init__()
        kwargs["path"] = self.path
        return super(BaseUploadFormSet, self)._construct_form(i, **kwargs)
    

class UploadForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        self.path = kwargs['path']
        del kwargs['path']
        super(UploadForm, self).__init__(*args, **kwargs)
    
    file = forms.FileField(label=_(u'File'))
    use_image_generator = forms.BooleanField(label=_(u'Use Image Generator'), required=False)
    
    def clean_file(self):
        if self.cleaned_data['file']:
            filename = convert_filename(self.cleaned_data['file'].name)
            
            # CHECK IF FILE EXISTS
            dir_list = os.listdir(self.path)
            if filename in dir_list:
                raise forms.ValidationError(_(u'File already exists.'))
                
            # TODO: CHECK IF VERSIONS_PATH EXISTS (IF USE_IMAGE_GENERATOR IS TRUE)
            
            # CHECK FILENAME
            if not alnum_name_re.search(filename):
                raise forms.ValidationError(_(u'Filename is not allowed.'))
                
            # CHECK EXTENSION / FILE_TYPE
            file_type = get_file_type(filename)
            if not file_type:
                raise forms.ValidationError(_(u'File extension is not allowed.'))
                
            # CHECK FILESIZE
            filesize = self.cleaned_data['file'].size
            if filesize > MAX_UPLOAD_SIZE:
                raise forms.ValidationError(_(u'Filesize exceeds allowed Upload Size.'))
        return self.cleaned_data['file']

