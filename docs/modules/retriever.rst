Retriever
=============

The ``retrievers`` folder of the ``data-provider`` contains a series of specific ``Retriever`` objects, designed to fetch data from multiple data sources using an existing API or, when it does not exist, reading data from a local file. If the user wants to add a new data source, they might create a new ``Retriever`` object which should have
   - a ``retrieve`` method (with multiple custom arguments);
   - a coordinate reference system ``crs`` attribute under the form of an epsg code or a pyproj string;
   - a ``sources`` attribute displaying the possible muliple sources accessible with the ``Retriever`` object (for example, the ``NWPRetriever`` can fetch data from COSMO-1E or ICON-CH1-EPS models);
   - a ``variables`` attribute showing the mapping between source variables and their ICON-CH1-EPS or COSMO-1E counterparts (see https://meteoswiss.atlassian.net/wiki/spaces/Nowcasting/pages/370049179/Data+model+for+output+parameters).
The ``DataRetriever`` iterates through its ``subretrievers`` attribute to find the right ``Retriever`` object to call for the given source and dates.

.. automodule:: weathermart.retrieve
   :members:
   :noindex:
