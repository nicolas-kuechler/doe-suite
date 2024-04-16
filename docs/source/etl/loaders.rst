

Loaders
=======
The `Loader` stage can be used to create visualizations, plots, and other files based on the data frame from the `Transformer` stage.

Save as Csv
-----------

.. autopydantic_model:: doespy.etl.steps.loaders.CsvSummaryLoader
    :exclude-members: load

Save as Pickle
--------------

.. autopydantic_model:: doespy.etl.steps.loaders.PickleSummaryLoader
    :exclude-members: load

Save as Latex Table
-------------------

.. autopydantic_model:: doespy.etl.steps.loaders.LatexTableLoader
    :exclude-members: load


Advanced Plots: Column Cross
----------------------------

The most flexible `Loader` is a project-specific loader tailored precisely to its requirements.
However, many projects share similar needs when it comes to visualizing data frames.
To streamline this process and help with best-practices, we introduce an extensible, universal solution: the ``ColumnCrossPlotLoader``.

This versatile `Loader` empowers users to create a diverse array of plots, including various forms of bar charts.
By configuring parameters within the ETL step, users can customize the ``ColumnCrossPlotLoader`` to suit their specific needs.

See `demo_project/doe-suite-config/super_etl/demo02-colcross.yml` for an example of how to configure the ``ColumnCrossPlotLoader``.

Moreover, the ``ColumnCrossPlotLoader`` offers multiple hooking points, enabling further customization through the integration of custom code.
This ensures that users have the flexibility to leverage the basic features even if they have a highly specialized requirement.
See `demo_project/doe-suite-config/does_etl_custom/etl/plots/colcross.py` for an example of how to extend the loader with custom components.


.. autopydantic_model:: doespy.etl.steps.colcross.colcross.ColumnCrossPlotLoader
    :inherited-members: BaseModel


Configurations (Cumulative)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `ColumnCrossPlotLoader` facilitates the creation of multiple figures, potentially containing grids of subplots, each presenting a chart composed of multiple artists.

To ensure maximum customization flexibility, the loader allows to configure every aspect separately.
This is achieved through cumulative lists, that are merged to establish configurations for figure-level attributes, subplot-level attributes, and individual artists.

The configurations are merged cumulatively, giving priority to those listed earlier in case of conflicts.
Leveraging the ``jp_query`` within list entries enables the creation of specific configurations tailored to the data used for their generation.

Each figure, subplot, and artist (e.g., a bar segment in a stacked bar chart) is assigned a unique identifier based on the underlying data.
These identifiers can be used to address particular configurations to subsets of plots, subplots, and artists.

For instance, subplots may have different chart types, or specific bars may require distinct colors.
Hence, by formulating a ``jp_query`` that matches on the identifer of a specific bar, we can apply a unique color to that bar.

Conceptually, the generation process is a hierarchical series of groupby operations.
At each level, an ID is assigned -- a flat JSON/dictionary object comprising key-value pairs derived from the grouping columns of the current level and all preceding levels.
For instance, if figures are created for each unique value in the 'year' column, resulting identifiers follow the format ``plot_id = {'year': 2000}`` or ``plot_id = {'year': 2001}``.

In addition to the grouping columns, IDs include supplementary information, such as the row and column indices of a subplot within a grid.

Below we show the hierarchical structure of the IDs, starting from the top-level figure and descending to the lowest-level artist:

..  tabs::

    ..  tab:: Generic

        .. code-block:: none
            :emphasize-lines: 2,4,6,8,10,11,14,18

            GroupBy Figure Cols
            ├── Figure1
            |   GroupBy Subplot Cols
            │   ├── Subplot1
            │   │   GroupBy Group Cols
            │   │   ├── Group1
            |   |   |   GroupBy Element Cols
            |   │   │   ├── Element1
            |   │   │   │   GroupBy Part Cols
            |   │   │   │   ├── Artist1
            |   │   │   │   └── Artist2
            |   │   ...
            |   |
            │   ├── Subplot2
            │   │   GroupBy Group Cols
            |   ...
            |
            ├── Figure2
            |   GroupBy Subplot Cols
            │   └── ...
            |
            |   ...

    ..  tab:: Example

        An example featuring a single figure comprising two subplots positioned side by side.
        One subplot showcases a grouped stacked bar chart, while the other contains a simple bar chart.


        .. image:: colcross.png
            :width: 800
            :alt: Alternative text

        .. code-block:: sh
            :emphasize-lines: 2,4,6, 9, 11, 12, 14, 16,17, 19, 22, 24,25, 27, 29, 30, 33, 35,36

            GroupBy Figure Cols
            └── Figure1 # only one figure
                GroupBy Metric [Time, Memory] # subplot cols
                ├── Subplot1 -> Time # [row_idx=0, col_idx=0] # grouped stacked bar chart
                │   GroupBy System Config [v1, v2] # group cols
                │   ├── BarGroup1 -> v1
                |   |   GroupBy Workload [wl1, wl2] # bar cols
                │   |   |
                │   │   ├── Bar1 -> wl1
                │   │   │   GroupBy part [overhead, base] # part cols
                │   │   │   ├── BarPart1 -> overhead # Artist1
                │   │   │   └── BarPart2 -> base     # Artist2
                |   |   |
                │   │   └── Bar2 -> wl2
                │   │       GroupBy part [overhead, base] # part cols
                │   │       ├── BarPart1 -> overhead # Artist1
                │   │       └── BarPart2 -> base     # Artist2
                |   |
                │   └── BarGroup2 -> v2
                |       GroupBy Workload [wl1, wl2] # bar cols
                │       |
                │       ├── Bar1 -> wl1
                │       │   GroupBy part [overhead, base] # part cols
                │       │   ├── BarPart1 -> overhead # Artist1
                │       │   └── BarPart2 -> base     # Artist2
                |       |
                │       └── Bar2 -> wl2
                │           GroupBy part [overhead, base] # part cols
                │           ├── BarPart1 -> overhead # Artist1
                │           └── BarPart2 -> base     # Artist2
                |
                |
                └── Subplot2 -> Memory # [row_idx=0, col_idx=1] # simple bar chart (no groups, no stacks)
                    GroupBy Workload [wl1, wl2] # bar cols
                    ├── Bar1 -> wl1 # Artist1
                    └── Bar2 -> wl2 # Artist2





..  tabs::

    ..  tab:: Plot Id

        .. code-block:: python

            # fig_foreach:
            #   cols: [col1, col2]

            plot_id = {'col1': '<value>', 'col2': '<value>'}

        Where ``col1`` and ``col2`` are the columns used to group the data frame, and ``<value>`` is the unique value of the group.

    ..  tab:: Subplot Id

        .. code-block:: py

            # fig_foreach:
            #   cols: [col1, col2]

            # subplot_grid:
            #   rows: [col3, $metrics$]
            #   cols: [col4]

            # metrics:
            #   time: ...
            #   memory: ...

            subplot_id = {
                # figure level
                'col1': '<value>', 'col2': '<value>',

                # subplot level
                'col3': '<value>', 'col4': '<value>',
                'subplot_row_idx': '<idx>', 'subplot_col_idx': '<idx>', # grid position
                '$metrics$': '<metric.name>', '$metric_unit$': '<metric.unit_label>' # metric info
            }

        Where ``col1, col2, col3, col4`` are the columns in the data frame, and ``<value>`` is a corresponding value.
        The ``subplot_row_idx`` and ``subplot_col_idx`` are the row and column indices of the subplot within the grid.

        Each subplot always has a single metric, which describe the data columns used to generate the chart.
        The special keyword ``$metrics$`` can be used in ``plot_foreach```or ``subplot_grid`` to specify how multiple metrics are handled.
        The respective id, contains the key ``$metrics$`` with the metric name, and ``$metric_unit$`` with the metric unit label.


    ..  tab:: Group Id (Chart Type Specific)

        Which ids are available below the subplot level depends on the chart type.
        However, a typical id could be for a group (e.g., group of bars).

        .. code-block:: py

            # fig_foreach:
            #   cols: [col1, col2]

            # subplot_grid:
            #   rows: [col3, $metrics$]
            #   cols: [col4]

            # metrics:
            #   time: ...

            # as part of the chart:
            # group_foreach:
            #   cols: [col5, col6]


            group_id = {
                # figure level
                'col1': '<value>', 'col2': '<value>',

                # subplot level
                'col3': '<value>', 'col4': '<value>',
                'subplot_row_idx': '<idx>', 'subplot_col_idx': '<idx>', # grid position
                '$metrics$': '<metric.name>', '$metric_unit$': '<metric.unit_label>' # metric info

                # group level
                'col5': '<value>', 'col6': '<value>',
            }



Plot Config
"""""""""""


.. autopydantic_model:: doespy.etl.steps.colcross.colcross.PlotConfig
    :inherited-members: BaseModel


Subplot Config
""""""""""""""

.. autopydantic_model:: doespy.etl.steps.colcross.colcross.SubplotConfig
    :inherited-members: BaseModel

Artist Config
"""""""""""""

.. autopydantic_model:: doespy.etl.steps.colcross.components.ArtistConfig
    :inherited-members: BaseModel


Supported Chart Types
^^^^^^^^^^^^^^^^^^^^^


Grouped Stacked Bar Chart
"""""""""""""""""""""""""

.. autopydantic_model:: doespy.etl.steps.colcross.subplots.bar.GroupedStackedBarChart
    :inherited-members: BaseModel


Grouped Boxplot
"""""""""""""""

.. autopydantic_model:: doespy.etl.steps.colcross.subplots.box.GroupedBoxplotChart
    :inherited-members: BaseModel


Additional Components
^^^^^^^^^^^^^^^^^^^^^

.. autopydantic_model:: doespy.etl.steps.colcross.components.DataFilter
    :inherited-members: BaseModel

.. autopydantic_model:: doespy.etl.steps.colcross.components.ColsForEach
    :inherited-members: BaseModel

.. autopydantic_model:: doespy.etl.steps.colcross.components.SubplotGrid
    :inherited-members: BaseModel
    :exclude-members: WidthHeight

.. autopydantic_model:: doespy.etl.steps.colcross.components.Metric
    :inherited-members: BaseModel



.. autopydantic_model:: doespy.etl.steps.colcross.components.LabelFormatter
    :inherited-members: BaseModel

.. autopydantic_model:: doespy.etl.steps.colcross.components.LegendConfig
    :inherited-members: BaseModel

.. autopydantic_model:: doespy.etl.steps.colcross.components.AxisConfig
    :inherited-members: BaseModel



Extending the ColumnCrossPlotLoader
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `ColumnCrossPlotLoader` module is designed with extensibility in mind, allowing for project-specifc customizations through hooks at various stages of the plot generation.
By leveraging these hooks, developers can integrate custom functions to modify plot configurations or introduce additional elements.
We showcase this functionality with an example, where the objective is to include a watermark label on each subplot.
See the :download:`resulting Bar Plot with Watermark <../../../demo_project/doe-suite-results-super/demo02-colcross/custom/$metrics$=time.pdf>`.

Here how it's achieved:

* We extend the `SubplotConfig` with a `watermark` attribute (so that we can define the content of the watermark from the `yaml` config of the step).

* We create a new loader, `MyCustomColumnCrossPlotLoader,` which replaces the default `SublotConfig` with the custom config containing the watermark.

* We register a new function that adds the watermark to the subplot. We register it in the `CcpHooks.SubplotPostChart` hook, which is called after the chart has been created in the subplot.

.. literalinclude:: ../../../demo_project/doe-suite-config/does_etl_custom/etl/plots/colcross.py
   :language: python
   :caption: demo_project/doe-suite-config/does_etl_custom/etl/plots/colcross.py
