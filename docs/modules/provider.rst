Provider
=========

The ``Provider``'s role is to call a ``Retriever`` object if the variables for the given source and dates provided by the users are not already in a local cache. The cache path must be provided by the user, or defaulted to the ``msclim`` cache on ``balfrin`` at this address: ``/store_new/msclim/pronos/``. The ``Provider`` object will then return the data to the user in the form of a ``xarray.Dataset`` object easily manipulable by the user.

.. automodule:: weathermart.provide
   :members:
   :noindex:
