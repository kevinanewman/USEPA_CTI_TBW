.. note::

    Works great within a virtual environment, so that no absolute paths are required in the make script

To create docs, run make.bat and specify the target build format...::

    make singlehtml
    make text

...and so on.

See https://www.sphinx-doc.org/en/master/man/sphinx-build.html for build types

Outputs will be in the doc bulid folder, i.e.::

    doc\build\singlehtml

