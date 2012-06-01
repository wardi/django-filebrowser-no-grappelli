# coding: utf-8

# django imports
from django.contrib.auth import get_user
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.importlib import import_module

def flash_login_required(function):
    """
    Decorator to recognize a user  by its session.
    Used for Flash-Uploading.
    """

    def decorator(request, *args, **kwargs):
        try:
            engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
        except:
            import django.contrib.sessions.backends.db
            engine = django.contrib.sessions.backends.db
        session_data = engine.SessionStore(request.POST.get('session_key'))
        user_id = session_data['_auth_user_id']
        # will return 404 if the session ID does not resolve to a valid user
        request.user = get_object_or_404(User, pk=user_id)
        return function(request, *args, **kwargs)
    return decorator

def flash_session_and_user_add(function):
    """
    Decorator to recognize a user and session by post session_key parameter.
    """
    
    def decorator(request, *args, **kwargs):
        engine = import_module(settings.SESSION_ENGINE)
        session_key = request.POST.get('session_key')
        request.session = engine.SessionStore(session_key) # request.session
        request.user = get_user(request)
        return function(request, *args, **kwargs)
    return decorator


