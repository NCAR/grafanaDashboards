import utils

from grafanalib.core import (
    Dashboard, RowPanel, Table,
    SqlTarget, GridPos, Time, PERCENT_FORMAT, PERCENT_UNIT_FORMAT
)

DATASOURCE="CasperTS"

def buildQuery(select, groupby="", metric="pbs_stathost", where=""):
    if groupby != "" and not groupby.startswith(","):
        groupby = ","+groupby
    if where != "" and not where.startswith("AND"):
        where = "AND "+where
    return f"""SELECT
  $__timeGroupAlias("time",$__interval),
  {select}
FROM {metric}
WHERE
  $__timeFilter("time") {where}
GROUP BY 1 {groupby}
ORDER BY 1
"""


def availUtil():
    query='''SELECT
    myquery.mytime AS "time",
    avg(metric) as {metric}
FROM
    (SELECT time_bucket_gapfill('10 minute', time, '${{__from:date}}', '${{__to:date}}') as mytime,
    COALESCE({select}, 0) AS metric
    FROM pbs_stathost
    WHERE time BETWEEN '${{__from:date}}' and '${{__to:date}}'
    GROUP BY mytime
    ) as myquery
GROUP BY "time"
ORDER BY "time";
'''
    gpuQuery='''SELECT
    myquery.mytime AS "time",
    avg(metric) as {metric},
    resources_available_gpu_model
FROM
    (SELECT time_bucket_gapfill('10 minute', time, '${{__from:date}}', '${{__to:date}}') as mytime,
    COALESCE({select}, 0) AS metric,
    resources_available_gpu_model
    FROM pbs_stathost
    WHERE time BETWEEN '${{__from:date}}' and '${{__to:date}}'
    GROUP BY mytime, resources_available_gpu_model
    ) as myquery
GROUP BY "time", resources_available_gpu_model
ORDER BY "time";
'''
    util = query.format(metric='util', select='''sum(CASE when jobs!='' THEN 1. ELSE 0. END)/count(state)''')
    avail = query.format(metric='avail', select='''avg(CASE when state ~* '(free|resv|job)' THEN 1. ELSE 0. END)''') 
    utilgpu = gpuQuery.format(metric='util', select='''sum(CASE when jobs!='' THEN 1. ELSE 0. END)/count(state)''')
    availgpu = gpuQuery.format(metric='avail', select='''avg(CASE when state ~* '(free|resv|job)' THEN 1. ELSE 0. END)''') 
    return (utils.getTimeSeriesWithLegend(queries=[
                                                  SqlTarget(rawSql=avail),
                                                  SqlTarget(rawSql=util)
                                                 ],
                                         title="Utilizatation and Availability",
                                         gridPos=GridPos(h=8, w=utils.WIDTH/2, x=0, y=0),
                                         unit=PERCENT_UNIT_FORMAT,
                                         datasource=DATASOURCE
                                         ),
            utils.getTimeSeriesWithLegend(queries=[
                                                  SqlTarget(rawSql=availgpu),
                                                  SqlTarget(rawSql=utilgpu)
                                                 ],
                                         title="Utilizatation and Availability by GPU type",
                                         gridPos=GridPos(h=8, w=utils.WIDTH/2, x=utils.WIDTH/2, y=0),
                                         unit=PERCENT_UNIT_FORMAT,
                                         datasource=DATASOURCE
                                         )
           )
def queSize():
    query = SqlTarget(rawSql="""
SELECT
  $__timeGroupAlias("time",$__interval),
  sum(transit) as transit,
  sum(queued) as queued,
  sum(held) as held,
  sum(waiting) as waiting,
  sum(running) as running,
  sum(exiting) as exiting,
  sum(begun) as begun
  FROM (
    SELECT
    time,
    que,
    split_part(split_part(state_count, ' ', 1), ':', 2)::integer as transit,
    split_part(split_part(state_count, ' ', 2), ':', 2)::integer as queued,
    split_part(split_part(state_count, ' ', 3), ':', 2)::integer as held,
    split_part(split_part(state_count, ' ', 4), ':', 2)::integer as waiting,
    split_part(split_part(state_count, ' ', 5), ':', 2)::integer as running,
    split_part(split_part(state_count, ' ', 6), ':', 2)::integer as exiting,
    split_part(split_part(state_count, ' ', 7), ':', 2)::integer as begun
  FROM pbs_statque
  WHERE
    $__timeFilter("time") AND total_jobs::integer > 0
  ) myQuery
GROUP BY time
ORDER BY time
""")
    return utils.getTimeSeries(queries=[query],
                                         title="Job states",
                                         gridPos=GridPos(h=8, w=utils.WIDTH/2, x=0, y=utils.HEIGHT),
                                         datasource=DATASOURCE
                                         )

def badNodes():
    newSql='''SELECT
  myquery.hostname,
  pbs_stathost.state,
  myquery.mytime as time
FROM
  (SELECT
    DISTINCT ON (hostname) hostname,
    max(time) as mytime
  FROM pbs_stathost
  WHERE time < to_timestamp($__unixEpochTo()) AND time > to_timestamp($__unixEpochFrom()) AND hostname != ''
  GROUP BY hostname
  ) as myquery
  INNER JOIN pbs_stathost on pbs_stathost.time=myquery.mytime AND pbs_stathost.hostname=myquery.hostname
WHERE 
  state !~ '^(free|job-busy|resv-exclusive)$' OR 
  mytime < to_timestamp($__unixEpochTo()-(5*60))'''
    nonJoin="""SELECT
  hostname,
  state,
  mytime as time
FROM
  (SELECT
    hostname,
    max(time) as mytime,
    state
  FROM pbs_stathost
  WHERE time < to_timestamp($__unixEpochTo()) AND time > to_timestamp($__unixEpochFrom()) AND hostname != ''
  GROUP BY hostname, state
  ORDER BY hostname, mytime DESC
  ) as myquery
WHERE 
  state !~ '^(free|job-busy|resv-exclusive)$' OR 
  mytime < to_timestamp($__unixEpochTo()-(5*60))
"""
    return  Table(
        maxDataPoints=1000,
        targets=[SqlTarget(rawSql=newSql)],
        dataSource=DATASOURCE,
        title="bad nodes",
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/2, x=utils.WIDTH/2, y=utils.HEIGHT)
    )

def gpu():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="100. * avg(resources_assigned_ngpus::float/resources_available_ngpus::float) as allocated",
           where="AND resources_available_ngpus != '0'",
           )),
        SqlTarget(rawSql=buildQuery(
           select="avg(utilization_gpu) as used",
           metric="nvidia_smi",
           where="AND host ~ '^(crhtc\d\d|casper\d\d)$'"
        )),
        SqlTarget(rawSql=buildQuery(
           select="100. * avg(memory_used)/avg(memory_total) as memory_used",
           metric="nvidia_smi",
           where="AND host ~ '^(crhtc\d\d|casper\d\d)$'"
        ))  
        ],
        title="GPU Allocated",
        unit=PERCENT_FORMAT,
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=0, y=0),
        datasource=DATASOURCE
    )

def cpu():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="100. * sum(resources_assigned_ncpus::float)/sum(resources_available_ncpus::float) AS allocated"
           )),
        SqlTarget(rawSql=buildQuery(
           select="100 - avg(usage_idle) AS used",
           metric="cpu",
           where="AND host ~ '^(crhtc\d\d|casper\d\d)$'"
        ))
        ],
        title="CPU Allocated",
        unit=PERCENT_FORMAT,
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=utils.WIDTH/3, y=0),
        datasource=DATASOURCE
    )

def mem():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="100. * avg(resources_assigned_mem::float/resources_available_mem::float) as allocated",
           where="AND resources_assigned_mem ~ '^\\d+$'",
           )),
        SqlTarget(rawSql=buildQuery(
           select="avg(used_percent) as used",
           metric="mem",
           where="AND host ~ '^(crhtc\d\d|casper\d\d)$'"
           )),
        ],
        title="Memory Allocated",
        unit=PERCENT_FORMAT,
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=2*utils.WIDTH/3, y=0),
        datasource=DATASOURCE
    )
    #utils.getTimeSeries(queries=[
    #    SqlTarget(rawSql="""SELECT
    #  time,
    #  substring(path from '\d+') as jobid,
    #  avg("memory.max_usage_in_bytes"::float/"memory.limit_in_bytes"::float) AS "max_used",
    #  avg("memory.usage_in_bytes"::float/"memory.limit_in_bytes"::float) AS "current"
    #FROM cgroup
    #WHERE
    #  $__timeFilter("time")
    #GROUP BY time, jobid
    #ORDER BY time"""),
    #    ],
    #    title="WIP Memory used by job",
    #    unit=PERCENT_UNIT_FORMAT,
    #    gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=2*utils.WIDTH/3, y=utils.HEIGHT),
    #    datasource=DATASOURCE
    #)

def users():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
            select="avg(n_users), host",
            metric="system",
            where="AND host ~ '^casper-login\d$'",
            groupby= ", host",
        ))],
        title="Users logged in",
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=0, y=0),
        datasource=DATASOURCE
    )

def disk():
#"""SELECT
#  $__timeGroupAlias("time",$__interval),
#  avg(used_percent),
#  host,
#  path
#FROM disk
#WHERE
#  $__timeFilter("time")
#GROUP BY 1, host, path
#ORDER BY 1"""
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="avg(used_percent), host, path",
           metric="disk",
           groupby="host, path"
           ),
        ),
        ],
        title="Disk Used",
        unit=PERCENT_FORMAT,
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH, x=0, y=utils.HEIGHT),
        datasource=DATASOURCE
    )

def infra_cpu():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="100 - avg(usage_idle) AS used, host",
           metric="cpu",
           groupby="host",
           where="AND host !~ '^(crhtc\d\d|casper\d\d)$'"
        ))
        ],
        title="CPU Used",
        unit=PERCENT_FORMAT,
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=utils.WIDTH/3, y=0),
        datasource=DATASOURCE
    )

def infra_mem():
#"""SELECT
#  $__timeGroupAlias("time",$__interval),
#  avg(used_percent) as used,
#  host
#FROM mem
#WHERE
#  $__timeFilter("time") AND host !~ '^(crhtc\d\d|casper\d\d)$'
#GROUP BY 1, host
#ORDER BY 1"""
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
            select="avg(used_percent) as used, host",
            metric="mem",
            groupby= "host",
            where="host !~ '^(crhtc\d\d|casper\d\d)$'",
            ),
        ),
        ],
        title="Mem Used",
        unit=PERCENT_FORMAT,
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=2*utils.WIDTH/3, y=0),
        datasource=DATASOURCE
    )


def dashboard():
    overview = RowPanel(
        title = "Overview",
        collapsed = True,
        panels=[*availUtil(), queSize(), badNodes()],
        gridPos=GridPos(h=2*utils.HEIGHT, w=utils.WIDTH, x=0, y=0)
    )

    resources = RowPanel(
        title = "Compute",
        collapsed = True,
        panels=[gpu(), cpu(), mem()],
        gridPos=GridPos(h=2*utils.HEIGHT, w=utils.WIDTH, x=0, y=2*utils.HEIGHT)
    )

    infra = RowPanel(
        title = "Infra",
        collapsed = True,
        panels=[users(), infra_mem(), infra_cpu(), disk()],
        gridPos=GridPos(h=2*utils.HEIGHT, w=utils.WIDTH, x=0, y=4*utils.HEIGHT)
    )

    return Dashboard(
        title="Casper",
        description="Casper dashboard",
        time=utils.INTERVAL,
        refresh='10m',
        sharedCrosshair=True,
        tags=[
            'generated',
            'casper'
        ],
        timezone="browser",
        panels=[ 
            overview,
            resources,
            infra
        ],
    ).auto_panel_ids()
