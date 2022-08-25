from grafanalib.core import (
    Dashboard, TimeSeries, RowPanel,
    SqlTarget, GridPos, Time, PERCENT_FORMAT, PERCENT_UNIT_FORMAT
)

INTERVAL=Time("now-8h", "now")
WIDTH=24
HEIGHT=8

def getTimeSeries(title, queries, gridPos, datasource, unit='', **kwargs):
    return TimeSeries(
        title = title,
        dataSource=datasource,
        maxDataPoints=1000,
        targets=queries,
        unit=unit,
        gridPos=gridPos,
        interval="5m",
        **kwargs
    )

def getTimeSeriesWithLegend(title, queries, gridPos, datasource, unit=''):
    return getTimeSeries(title, queries, gridPos, datasource, unit,
        legendPlacement="right",
        legendCalcs=["min","mean","max"],
        legendDisplayMode="table")
