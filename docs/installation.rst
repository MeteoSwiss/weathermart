.. highlight:: shell

============
Installation
============


This is written for usage on Balfrin.
============
Requirements
============
* pyenv: https://github.com/pyenv/pyenv
* poetry: https://python-poetry.org/docs/

If you didn't have these tools before, quickly restart your shell to assure poetry can find pyenv.

With poetry and pyenv ready, run ``./install.sh``. This will install the correct python version including the requirements for ``sqlite3`` and ``lzma``, the poetry package **with all extras** and ``pre-commit``.
In theory, you can also use the retriever with a python version without ``sqlite3`` and ``lzma`` if you don't plan to use the satellite retriever.

============
Extras
============

Some of the dependencies are split up into different extras.
By default, ``install.sh`` will install all extras.

+---------------------------+---------+
| Source                    | ``<XYZ>`` |
+===========================+=========+
| EUMETSAT API              | eumetsat|
+---------------------------+---------+
| Radar data (MCH, OPERA)   | radar   |
+---------------------------+---------+
| GRIB                      | eccodes |
+---------------------------+---------+
| DEM (Digital elevation model) | dem |
+---------------------------+---------+
