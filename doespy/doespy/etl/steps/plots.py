
import typing
import jmespath
from matplotlib import pyplot as plt
import pandas as pd

from typing import Dict, List, Tuple, Union

from doespy.design.etl_design import MyETLBaseModel
from doespy.etl.steps.loaders import PlotLoader


from dataclasses import dataclass

from pydantic import Field, validator





class DataFilter(MyETLBaseModel):

     allowed: Dict[str, List[str]]

     def apply(self, cols: List[str], df: pd.DataFrame) -> pd.DataFrame:

        n_rows_intial = len(df)
        df_filtered = df.copy()

        cols_values = [(col, self.allowed.get(col, None)) for col in cols]

        # filter out non-relevant results
        for col, allowed in cols_values:

            # convert column to string for filtering
            try:
                df_filtered[col] = df_filtered[col].astype(str)
            except KeyError:
                raise KeyError(f"col={col} not in df.columns={df.columns}")

            all_values = df_filtered[col].unique().tolist()

            if allowed is None:
                allowed = all_values

            # filter out non-relevant results
            df_filtered = df_filtered[df_filtered[col].isin(allowed)]

            remaining_values = set(df_filtered[col].unique().tolist())

            removed_values =  set(all_values) - remaining_values

            if removed_values:
                print(f"Filtering {col} to {allowed}   (remaining values: {remaining_values}  |  removed values: {removed_values})")

            # convert to categorical
            df_filtered[col] = pd.Categorical(df_filtered[col], ordered=True, categories=allowed)
        df_filtered.sort_values(by=cols, inplace=True)

        print(f"Filtered out {n_rows_intial - len(df_filtered)} rows, now there are {len(df_filtered)} remaining rows")

        return df_filtered


class LabelFormatter(MyETLBaseModel):

    template: str
    """A template string that can contain placeholders in the form "{placeholder}".
    The placehold correspond to column names (which are presend in the data_id)
    """

    kwargs: Dict[str, str] = Field(default_factory=dict)
    """Additional keyword arguments that will be passed to the matplotlib function that is used to set the labels.
    """

    def apply(self, data_id: Dict[str, str], label_lookup: Dict[str, str], info: str) -> str:
        #template string: "Hello {name}"
        labels = {k:label_lookup.get(lbl, lbl) for k, lbl in data_id.items()}

        try:
            lbl = self.template.format(**labels)
        except KeyError as e:
            raise KeyError(f"LabelFormatter: {info}: Could not find all keys in data_id: {data_id}  (label_lookup={label_lookup})") from e
        return lbl


class Metric(MyETLBaseModel):

    value_cols: Union[str, List[str]]
    error_cols: Union[str, List[str]] = None

    @validator('value_cols', 'error_cols', pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v

class ColsForEach(MyETLBaseModel):

    cols: List[str]

    jp_except: str = None
    """Skip certain combinations based on the data id (and parent data_id)
    """

    label: LabelFormatter = None

    def get_cols(self):
        return self.cols.copy()

    def for_each(self, df: pd.DataFrame, parent_id: Dict[str, str]):

        if not self.cols: # is empty
            yield 0, df, {}
        else:
            cols = self.cols[0] if len(self.cols) == 1 else self.cols

            i = 0
            for idx, df1 in df.groupby(cols):
                idx = (idx, ) if not isinstance(idx, tuple) else idx
                data_id = {k: v for k, v in zip(self.cols, list(idx), strict=True)}
                all_id = {**parent_id, **data_id}
                if self.jp_except is None or not is_match(self.jp_except, all_id, info="jp_except"):
                    yield i, df1, data_id
                    i += 1
                else:
                    print(f"Skipping {all_id} due to jp_except={self.jp_except}")



class SubplotForEach(MyETLBaseModel):

    rows: List[str]
    cols: List[str]

    def init(self):
        # TODO
        pass

    def for_each(self, df1: pd.DataFrame):
        pass # TODO


class GroupedStackedBarChart(MyETLBaseModel):

    group_foreach: ColsForEach = ColsForEach(cols=[])

    bar_foreach: ColsForEach

    part_foreach: ColsForEach = ColsForEach(cols=[])
    """
    "
    if part_foreach is None, i.e., default, then only the $metrics$ columns will be used as bar parts
    """

    bar_width: float = 0.6
    group_padding: float = 0.1

    def get_cols(self):
        return self.group_foreach.get_cols() + self.bar_foreach.get_cols() + self.part_foreach.get_cols()


    def plot(self, ax: plt.Axes, df1: pd.DataFrame, data_id: Dict[str, str], metric: Metric, parent):
        group_ticks = set()
        bar_ticks = set()

        for part_value, part_error, position, bar_group_id, bar_id, bar_part_id in self.for_each(df1, metric=metric, subplot_id=data_id):

            full_id = {**data_id, **bar_group_id, **bar_id, **bar_part_id}
            # print(f"{full_id=}")

            style_config = parent.cum_artist_style.apply(full_id, info="cum_artist_style") if parent.cum_artist_style is not None else {}

            label = style_config.pop("label", parent.legend_label.apply(full_id, label_lookup=parent.label_map, info="legend_label"))

            ax.bar(position.bar_center_pos, part_value, width=self.bar_width, label=label, yerr=part_error,  bottom=position.bar_part_bottom, **style_config)

            if self.group_foreach.label is not None:
                group_lbl = self.group_foreach.label.apply({**data_id, **bar_group_id}, label_lookup=parent.label_map, info="group_label")
                group_ticks.add((position.group_center_pos, group_lbl))

            if self.bar_foreach.label is not None:
                bar_lbl = self.bar_foreach.label.apply({**data_id, **bar_group_id, **bar_id}, label_lookup=parent.label_map, info="bar_label")
                bar_ticks.add((position.bar_center_pos, bar_lbl))

        # X-Axis Ticks
        if group_ticks:
            group_xticks, group_labels = zip(*group_ticks)
            ax.set_xticks(group_xticks, labels=group_labels, **self.group_foreach.label.kwargs)

        if bar_ticks:
            is_minor = group_ticks

            bar_xticks, bar_labels = zip(*bar_ticks)
            ax.set_xticks(bar_xticks, labels=bar_labels, minor=is_minor, **self.bar_foreach.label.kwargs)


    def for_each(self, df1: pd.DataFrame, metric: Metric, subplot_id: Dict[str, str]):

        @dataclass
        class BarPartPosition:

            group_center_pos: float

            bar_left_pos: float
            bar_center_pos: float

            bar_part_bottom: float


        bar_left_pos, bar_center_pos, group_center_pos = self._calc_positions(df1, subplot_id=subplot_id)

        i_bar = 0

        for i_group, df_bar_group, bar_group_id in self.group_foreach.for_each(df1, parent_id=subplot_id):

            for _i_bar, df_bar, bar_id in self.bar_foreach.for_each(df_bar_group, parent_id={**subplot_id, **bar_group_id}):

                bottom = 0

                for _i_part, df_bar_part, part_id in self.part_foreach.for_each(df_bar, parent_id={**subplot_id, **bar_group_id, **bar_id}):

                    if len(df_bar_part) < 1:
                        continue

                    assert len(df_bar_part) == 1, f"Dataframe must have only one row to be used as a bar part by columns  (df={df_bar_part})  ({bar_group_id=}, {bar_id=}, {part_id=})"

                    error_cols = metric.error_cols if metric.error_cols is not None else [None] * len(metric.value_cols)

                    for value_col, error_col in zip(metric.value_cols, error_cols, strict=True):

                        bar_part_id = {**part_id, "value_col": value_col, "error_col": error_col}

                        part_value = df_bar_part[value_col].iloc[0]
                        part_error = df_bar_part[error_col].iloc[0] if error_col is not None else None

                        position = BarPartPosition(
                            group_center_pos=group_center_pos[i_group],
                            bar_left_pos=bar_left_pos[i_bar],
                            bar_center_pos=bar_center_pos[i_bar],
                            bar_part_bottom=bottom
                        )

                        bottom += part_value

                        yield part_value, part_error, position, bar_group_id, bar_id, bar_part_id

                i_bar += 1




    def _calc_positions(self, df1: pd.DataFrame, subplot_id: Dict[str, str]):

        # positioning
        bar_info = [] # [3, 2, 3] -> 3 bars in first group, 2 in second, 3 in third

        bar_center_pos = []
        group_center_pos = [] # the center of each group

        pos = 0

        for _i_group, df_bar_group, bar_group_id in self.group_foreach.for_each(df1, parent_id=subplot_id):
            n_bars_per_group = 0

            group_start_pos = pos
            group_end_pos = pos

            for _i_bar, _df_bar, _bar_id in self.bar_foreach.for_each(df_bar_group, parent_id={**subplot_id, **bar_group_id}):
                n_bars_per_group += 1

                bar_center_pos.append(pos)
                group_end_pos = pos
                pos += self.bar_width

            # [2, 2.5, 3, 3.5] => 5.5 / 2 = 2.75
            # [2, 2.5, 3, 3.5, 4] => 6 / 2 = 3
            group_center_pos.append((group_start_pos + group_end_pos) / 2)

            pos += self.group_padding

            bar_info.append(n_bars_per_group)

        bar_left_pos = [x - self.bar_width / 2 for x in bar_center_pos] # + self.bar_width / 2

        return bar_left_pos, bar_center_pos, group_center_pos


def is_match(jp_query, data_id, info) -> bool:

    if jp_query is None:
        #print(f"JmesPathFilter: {info}: query is None")
        return True

    #print(f"JmesPathFilter: {info}: query={self.jp_query}  data_id={data_id}")

    result = jmespath.search(jp_query, data_id)
    #print(f"JmesPathFilter: {info}: query is {result}    {jp_query=}")
    assert isinstance(result, bool), f"JmesPathFilter: {info}: query={jp_query} returned non-boolean result: {result}"
    return result


# TODO [nku] is class necessary? -> should this be a root data type?
class JmesPathFilter(MyETLBaseModel):

    jp_query: str = None

    def is_match(self, data_id, info) -> bool:

        return is_match(self.jp_query, data_id, info)


class DictApplyFilter(JmesPathFilter):

    config: Dict[str, typing.Any]

    def empty_config(self):
        return dict()

    def update_config_if_match(self, config: Dict[str, typing.Any], data_id, info) -> bool:

        if self.is_match(data_id, info):
            # overwriting existing keys
            config.update(self.config)

class CumulativeApplyFilter(MyETLBaseModel):

    __root__: List[DictApplyFilter]

    def apply(self, data_id, info):

        config = None

        # loop in reverse order to give the first filter the highest priority
        for filter in reversed(self.__root__):
            if config is None:
                config = filter.empty_config()

            filter.update_config_if_match(config, data_id, info)
        return config




class SubplotConfig(JmesPathFilter):

    #subplot: SubplotForEach

    # select chart type
    chart: Union[GroupedStackedBarChart] = None # TODO: could add others laters

    label_map: Dict[str, str] = None #Field(default_factory=dict)

    ax_title: LabelFormatter = None

    legend_label: LabelFormatter = None

    cum_artist_style: CumulativeApplyFilter = None

    def fill_missing(self, other):
        for k, v in self.dict().items():
            if v is None:
                setattr(self, k, getattr(other, k))


def convert_metrics(metrics: Dict[str, Metric], df: pd.DataFrame):
    """
    Introduce a duplicate of the df for each metric and mark it with a new column $metrics$.
    -> this allows to use $metrics$ as a column to generate different plots / subplots / groups / etc.
    """


    df1 = None

    for metric_name, metric in metrics.items():

        df_copy = df.copy()
        df_copy["$metrics$"] = metric_name

        assert set(metric.value_cols).issubset(df.columns), f"Metric Value Columns: Some columns not found in DataFrame. Missing: {set(metric.value_cols) - set(df.columns)}"
        if metric.error_cols is not None:
            assert set(metric.error_cols).issubset(df.columns), f"Metric Error Columns: Some columns not found in DataFrame. Missing: {set(metric.error_cols) - set(df.columns)}"

        df1 = pd.concat([df1, df_copy], axis=0) if df1 is not None else df_copy

    return df1




class ForEachPlotLoader(PlotLoader):

    data_filter: DataFilter
    fig_foreach: ColsForEach

    metrics: Dict[str, Metric]

    # TODO [nku] add subplots here

    cum_config: List[SubplotConfig]


    def merge_cum_config(self, data_id):

        # for each ax (i.e., subplot) determine the config by merging the configs where the filter matches
        config = None
        # TODO [nku] define which one should have higher prio (e.g., the first or the last)
        for cfg in self.cum_config:
            if cfg.is_match(data_id, "ax"):
                if config is None:
                    config = cfg
                else:
                    config.fill_missing(cfg)
        return config

    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if df.empty:
            return

        cols = self.fig_foreach.get_cols()
        for cfg in self.cum_config:
            if cfg.chart is not None:
                cols += cfg.chart.get_cols()

        if self.metrics is not None:
            df = convert_metrics(self.metrics, df)

        df = self.data_filter.apply(cols=cols, df=df)



        # TODO [nku] we currently don't have any aggregation option here (e.g., mean, std, etc.)

        for _i_plot, df_plot, plot_id in self.fig_foreach.for_each(df, parent_id={}):

            print(f"{plot_id=}")

            ax_id = {}


            # NOTE: each subplot and thus each artist has one metric

            subplot_id = {**plot_id, **ax_id}

            config = self.merge_cum_config(subplot_id)


            fig, ax = plt.subplots(1, 1)
            subplot_idx = (0, 0)

            config.chart.plot(ax=ax, df1=df_plot, data_id=subplot_id, metric=self.metrics[subplot_id["$metrics$"]], parent=config)


            ###################### Labeling Start ######################

            if config.ax_title is not None:
                ax.set_title(config.ax_title.apply({**plot_id, **ax_id}, label_lookup=config.label_map, info="ax_title"))

            if config.legend_label is not None:
                handles, labels = ax.get_legend_handles_labels()
                # remove duplicates
                unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]

                ax.legend(*zip(*unique), **config.legend_label.kwargs)

            ###################### Labeling End ######################



#class BarPlotLoader(PlotLoader):
#
#    data_filter: DataFilter
#    plot: PlotForEach
#    #subplot: SubplotForEach
#
#    # TODO [nku] currently I don't have a mechanism to control subplot differences in styling -> the logic could just set the respective fields
#
#    grouped_stacked_bar_chart: GroupedStackedBarChart
#
#    label_map: Dict[str, str] = Field(default_factory=dict)
#
#    ax_title: LabelFormatter = None
#
#    legend_label: LabelFormatter = None
#
#    cum_artist_style: CumulativeApplyFilter = None
#
#    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
#        if df.empty:
#            return
#
#        cols = self.plot.get_cols() + self.grouped_stacked_bar_chart.get_cols()
#
#        df = self.data_filter.apply(cols=cols, df=df)
#
#
#        # TODO [nku] we currently don't have any aggregation option here (e.g., mean, std, etc.)
#
#        for idx_plot, df_plot, plot_id in self.plot.for_each(df):
#
#            #for idx_ax, df_ax, ax_id in self.subplot.for_each(df):
#
#            ax_id = {}
#
#            fig, ax = plt.subplots(1, 1)
#            subplot_idx = (0, 0)
#
#
#            group_ticks = set()
#            bar_ticks = set()
#
#            for part_value, part_error, position, bar_group_id, bar_id, bar_part_id in self.grouped_stacked_bar_chart.for_each(df_plot):
#
#                full_id = {**plot_id, **ax_id, **bar_group_id, **bar_id, **bar_part_id}
#                # print(f"{full_id=}")
#
#                style_config = self.cum_artist_style.apply(full_id, info="cum_artist_style") if self.cum_artist_style is not None else {}
#
#                label = style_config.pop("label", self.legend_label.apply(full_id, label_lookup=self.label_map, info="legend_label"))
#
#                ax.bar(position.bar_center_pos, part_value, width=self.grouped_stacked_bar_chart.bar_width, label=label, yerr=part_error,  bottom=position.bar_part_bottom, **style_config)
#
#                if self.grouped_stacked_bar_chart.group_label is not None:
#                    group_lbl = self.grouped_stacked_bar_chart.group_label.apply({**plot_id, **ax_id, **bar_group_id}, label_lookup=self.label_map, info="group_label")
#                    group_ticks.add((position.group_center_pos, group_lbl))
#
#                if self.grouped_stacked_bar_chart.bar_label is not None:
#                    bar_lbl = self.grouped_stacked_bar_chart.bar_label.apply({**plot_id, **ax_id, **bar_group_id, **bar_id}, label_lookup=self.label_map, info="bar_label")
#                    bar_ticks.add((position.bar_center_pos, bar_lbl))
#
#
#
#
#
#            ###################### Labeling Start ######################
#            if group_ticks:
#                group_xticks, group_labels = zip(*group_ticks)
#                ax.set_xticks(group_xticks, labels=group_labels, **self.grouped_stacked_bar_chart.group_label.kwargs)
#
#            if bar_ticks:
#                is_minor = group_ticks
#
#                bar_xticks, bar_labels = zip(*bar_ticks)
#                ax.set_xticks(bar_xticks, labels=bar_labels, minor=is_minor, **self.grouped_stacked_bar_chart.bar_label.kwargs) # TODO: should only be minor if it has a group label
#
#            if self.ax_title is not None:
#                ax.set_title(self.ax_title.apply({**plot_id, **ax_id}, label_lookup=self.label_map, info="ax_title"))
#
#            if self.legend_label is not None:
#                handles, labels = ax.get_legend_handles_labels()
#                # remove duplicates
#                unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]
#
#                ax.legend(*zip(*unique), **self.legend_label.kwargs)
#
#            ###################### Labeling End ######################
#