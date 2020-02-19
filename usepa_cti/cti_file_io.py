# -*- coding: utf-8 -*-
"""

cti_file_io.py
==============

File system routines for general use, collects functionality from sys, os and shutil

.. note::

    This is development code written by EPA staff and
    is intended only for evaluation purposes—it does not
    represent how we may or may not use the resulting
    output in the development or promulgation of future rules

@author: US EPA

"""

from __init__ import *

if cti_verbose:
    print('Loading %s...' % __name__)

import sys
import os
import shutil


def delete_folder(dstfolder):
    """
    Delete the file system folder and all its contents

    :param dstfolder: pathname of folder to delete
    """
    shutil.rmtree(dstfolder, ignore_errors=True)


def validate_folder(dstfolder):
    """
    Verify the existence of a folder and try to create it if doesn't exist

    .. code-block:: python

        validate_folder('C:\\Users\\Temp')

    :param dstfolder: Path the folder to validate/create

    .. attention:: Exits app on failure
    """
    if not os.access(dstfolder, os.F_OK):
        try:
            os.makedirs(dstfolder, exist_ok=True) # try create folder if necessary
        except:
            print("Couldn't access or create {}".format(dstfolder),file=sys.stderr)
            exit(-1)


def validate_file(filename):
    """
    Verify the existence of file, exit app on failure

    :param filename: File pathname of the file to validate

    .. warning:: Exits app on failure
    """
    if not os.access(filename, os.F_OK):
        print("\n*** Couldn't access {}, check path and filename ***".format(filename), file=sys.stderr)
        exit(-1)


def file_exists(filename):
    """
    Verify the existence of filename

    :param filename: File pathname of the file to validate

    :returns True if file is accessible, else False

    """
    return os.access(filename, os.F_OK)


def get_filepath(filename):
    """
    Returns path to file, e.g. /somepath/somefile.txt -> /somepath

    :param filename: file name, including path to file as required
    :return: file path, not including the file name
    """
    return os.path.split(filename)[0]


def get_filepathname(filename):
    """
    Returns file name without extension, including path, e.g. /somepath/somefile.txt -> /somepath/somefile

    :param filename: file name, including path to file as required
    :return: file name without extension, including path
    """
    return os.path.splitext(filename)[0]


def get_filename(filename):
    """
    Returns file name without extension, e.g. /somepath/somefile.txt -> somefile

    :param filename: file name, including path to file as required
    :return: file name without extension
    """
    return os.path.split(get_filepathname(filename))[1]


def get_filenameext(filename):
    """
    Returns file name including extension, e.g. /somepath/somefile.txt -> somefile.txt

    :param filename: file name, including extension, including path to file as required
    :return: file name including extension
    """
    return os.path.split(filename)[1]


def get_parent_foldername(filepathnameext):
    """
    Returns the parent folder of the given file e.g. /apath/somepath/somefile.txt -> somepath

    :param filepathnameext: file name, including extension and path to file
    :return: parent folder of the given file
    """
    return get_filename(get_filepath(filepathnameext))


def network_copyfile(remote_path, srcfile):
    """
    Copy file to remote path

    :param remote_path: Path to file destination
    :param srcfile: source file name, including extension and path to file
    """
    dstfile = remote_path + os.sep + get_filenameext(srcfile)
    shutil.copyfile(srcfile, dstfile)


def relocate_file(remote_path, local_filename):
    """
    Move local file out to remote path and return the filename in that remote context

    :param remote_path: Path to file destination
    :param local_filename: local source file name, including extension and path to file as required
    """
    network_copyfile(remote_path, local_filename)
    return get_filenameext(local_filename)


def sysprint(str):
    """
    Performs ECHO command of str in CMD window

    :param str: string to echo
    """
    os.system('echo {}'.format(str))
