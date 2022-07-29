from grafanalib.core import (
    Dashboard, TimeSeries, RowPanel,
    SqlTarget, GridPos, Time, PERCENT_FORMAT, PERCENT_UNIT_FORMAT
)

DATASOURCE="BifrostTS"
INTERVAL=Time("now-3h", "now")
WIDTH=24
NUM_SPINES=6
NUM_LEAFS=10

def getTimeSeries(title, query, gridPos, unit='', **kwargs):
    return TimeSeries(
        title = title,
        dataSource=DATASOURCE,
        maxDataPoints=1000,
        targets=[
            SqlTarget(
                rawSql=query,
                refId="A",
            ),
        ],
        unit=unit,
        gridPos=gridPos,
        **kwargs
    )

def getTimeSeriesWithLegend(title, query, gridPos, unit=''):
    return getTimeSeries(title, query, gridPos, unit,
        legendPlacement="right",
        legendCalcs=["min","mean","max"],
        legendDisplayMode="table")


def overallBandwidth():
    bandwidthQuery="""SELECT
  $__timeGroupAlias(time,$__interval),
  hostname as metric,
  (sum("MyOctets") - lag(sum("MyOctets")) OVER (PARTITION BY hostname ORDER BY $__timeGroup(time,$__interval)))/(32*2) AS "TheOctets"
FROM (
  SELECT
    $__timeGroupAlias(time,$__interval),
    hostname,
    8*max("{}")/($__interval_ms/1000)/1000000000 AS "MyOctets"
  FROM
    counters
  WHERE
    $__timeFilter(time) AND
    "if-name" ~* '^swp[1-32]*|^eth0$'
  GROUP BY
  1, 2
) AS myquery
GROUP BY 1, hostname, 2
ORDER BY 1,2
"""
    return (getTimeSeriesWithLegend(query=bandwidthQuery.format("InOctets"),
                                    title="Ingress",
                                    gridPos=GridPos(h=8, w=WIDTH/2, x=0, y=0),
                                    unit=PERCENT_FORMAT),
            getTimeSeriesWithLegend(title="Egress",
                                    query=bandwidthQuery.format("OutOctets"),
                                    gridPos=GridPos(h=8, w=WIDTH/2, x=1 + (WIDTH/2), y=0),
                                    unit=PERCENT_FORMAT)
          )

def errorMetrics():
    # format with "In or Out"
    errorsQuery='''SELECT
  $__timeGroupAlias(time,$__interval),
  hostname AS metric,
  (CASE WHEN max("{}Errors") >= lag(max("{}Errors")) OVER (PARTITION BY hostname ORDER BY $__timeGroup(time,$__interval)) THEN max("{}Errors") - lag(max("{}Errors")) OVER (PARTITION BY hostname ORDER BY $__timeGroup(time,$__interval)) WHEN lag(max("{}Errors")) OVER (PARTITION BY hostname ORDER BY $__timeGroup(time,$__interval)) IS NULL THEN NULL ELSE max("{}Errors") END) AS """{}Errors"""
FROM counters
WHERE
  $__timeFilter(time)
GROUP BY 1, hostname,2
ORDER BY 1,2
'''
    discardsQuery='''SELECT
  $__timeGroupAlias(time,$__interval),
  hostname AS metric,
  (CASE WHEN max("{}Discards") >= lag(max("{}Discards")) OVER (PARTITION BY hostname ORDER BY $__timeGroup(time,$__interval)) THEN max("{}Discards") - lag(max("{}Discards")) OVER (PARTITION BY hostname ORDER BY $__timeGroup(time,$__interval)) WHEN lag(max("{}Discards")) OVER (PARTITION BY hostname ORDER BY $__timeGroup(time,$__interval)) IS NULL THEN NULL ELSE max("{}Discards") END) AS """{}Discards"""
FROM counters
WHERE
  $__timeFilter(time)
GROUP BY 1, hostname,2
ORDER BY 1,2'''
    return (getTimeSeries(query=errorsQuery.replace("{}","In"),
                          title="InErrors",
                          gridPos=GridPos(h=8, w=WIDTH/4,x=0,y=10)),
            getTimeSeries(query=discardsQuery.replace("{}","In"),
                          title="InDiscards",
                          gridPos=GridPos(h=8,w=WIDTH/4,x=WIDTH/4,y=10)),
            getTimeSeries(query=errorsQuery.replace("{}","Out"),
                          title="OutErrors",
                          gridPos=GridPos(h=8, w=WIDTH/4,x=WIDTH/2,y=10)),
            getTimeSeries(query=discardsQuery.replace("{}","Out"),
                          title="OutDiscards",
                          gridPos=GridPos(h=8,w=WIDTH/4,x=3*WIDTH/4,y=10))
           )

def switchMetrics(switch):
    query= '''SELECT
  $__timeGroupAlias(time,$__interval),
  "myLabel" as metric,
  sum("MyOctets") - lag(sum("MyOctets")) OVER (PARTITION BY "myLabel" ORDER BY $__timeGroup(time,$__interval)) AS "TheOctets"
FROM (
  SELECT
    $__timeGroupAlias(time,$__interval),
    concat("if-name", ' ', floor("speed"/1000), 'Gb') AS "myLabel",
    8*max("{}Octets")/($__interval_ms/1000)/(max("speed")*1000000) AS "MyOctets"
  FROM
    counters
  WHERE
    $__timeFilter(time) AND
    "if-name" !~* '^lo$|^bridge$|docker0|^mgmt$|^overlay|pimreg|^vlan|^vx-|^Intel|^ipmr-lo$|^mirror$|^swid0_eth$' AND
    hostname ~ 'switch' AND
    "speed" != 0
  GROUP BY
  1, 2
) AS myquery
GROUP BY 1, "myLabel", 2
ORDER BY 1,2'''
    return (getTimeSeriesWithLegend(query=query.format("In").replace("switch",switch), title=f"{switch} Ingress", gridPos=GridPos(h=8, w=WIDTH/2, x=0, y=0), unit=PERCENT_UNIT_FORMAT),
            getTimeSeriesWithLegend(query=query.format("Out").replace("switch",switch), title=f"{switch} Egress", gridPos=GridPos(h=8, w=WIDTH/2, x=WIDTH/2, y=0), unit=PERCENT_UNIT_FORMAT)
           )


def spineMetrics():
    metrics = ()
    for num in range(1, NUM_SPINES+1):
        metrics += switchMetrics(f"sp{num:02d}")
    return metrics

def leafMetrics():
    metrics = ()
    for num in range(1, NUM_LEAFS+1):
        metrics += switchMetrics(f"lf{num:02d}")
    return metrics

def dashboard():
    overview = RowPanel(
        title = "Overview",
        collapsed = True,
        panels=[*overallBandwidth(), *errorMetrics()],
        gridPos=GridPos(h=20, w=24, x=0, y=0)
    )
    
    spines = RowPanel(
        title = "Spines",
        collapsed = True,
        panels=[*spineMetrics()],
        gridPos=GridPos(h=60, w=24, x=0, y=20)
    )
    
    leafs = RowPanel(
        title = "Leafs",
        collapsed = True,
        panels=[*leafMetrics()],
        gridPos=GridPos(h=100, w=24, x=0, y=80)
    )
    
    return Dashboard(
        title="Bifrost",
        description="bifrost dashboard",
        time=INTERVAL,
        refresh=None,
        tags=[
            'generated',
            'bifrost'
        ],
        timezone="browser",
        panels=[
            overview,
            spines,
            leafs
        ],
    ).auto_panel_ids()
