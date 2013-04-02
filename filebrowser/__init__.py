# coding: utf-8

from threading import local
_dirs = local()


def get_default_dir():
    return getattr(_dirs, 'current_dir', u'')


def set_default_dir(dir):
    setattr(_dirs, 'current_dir', dir)
