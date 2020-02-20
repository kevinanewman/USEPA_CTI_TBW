Developer Notes
---------------

Install / Uninstall
+++++++++++++++++++

To install as a user::

    python setup.py install

or::

    pip install .

To install for development (debugging / updating autodocs, etc)::

    pip install .[dev]

To uninstall::

    pip uninstall usepa-cti

Version Bump
++++++++++++

From the project top-level, where bumpversion.cfg exists::

Commit files::

    git commit -m "commit before version bump" --all

Then::

    bumpversion patch --verbose

or::

    bumpversion minor --verbose

or::

    bumpversion major --verbose
