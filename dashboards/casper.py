import utils

from grafanalib.core import (
    Dashboard, TimeSeries, RowPanel,
    SqlTarget, GridPos, Time, PERCENT_FORMAT, PERCENT_UNIT_FORMAT
)

DATASOURCE="CasperTS"

def buildQuery(select, groupby="", metric="pbs_stathost", where=""):
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
    availSelect = """avg(CASE when state~* '(free|resv|job)' THEN 1. ELSE 0. END) as "Avail" """
    utilSelect = """sum(CASE when jobs!='' THEN 1. ELSE 0. END)/count(state) as "Util" """
    return (utils.getTimeSeriesWithLegend(queries=[
                                                  SqlTarget(rawSql=buildQuery(availSelect)),
                                                  SqlTarget(rawSql=buildQuery(utilSelect))
                                                 ],
                                         title="Utilizatation and Availability",
                                         gridPos=GridPos(h=8, w=utils.WIDTH/3, x=0, y=0),
                                         unit=PERCENT_UNIT_FORMAT,
                                         datasource=DATASOURCE
                                         ),
            utils.getTimeSeriesWithLegend(queries=[
                                                  SqlTarget(rawSql=buildQuery(select = availSelect + ", resources_available_gpu_model", groupby=", resources_available_gpu_model")),
                                                  SqlTarget(rawSql=buildQuery(select=utilSelect + ", resources_available_gpu_model", groupby=", resources_available_gpu_model"))
                                                 ],
                                         title="Utilizatation and Availability by GPU type",
                                         gridPos=GridPos(h=8, w=utils.WIDTH/3, x=utils.WIDTH/3, y=0),
                                         unit=PERCENT_UNIT_FORMAT,
                                         datasource=DATASOURCE
                                         )
           )
def queSize():
    return utils.getTimeSeries(queries=[SqlTarget(rawSql=buildQuery(select="""avg(total_jobs::integer) as "que", que as q""", groupby=", q",metric="pbs_statque", where="AND total_jobs::integer > 0"))],
                                         title="Total Jobs By Que",
                                         gridPos=GridPos(h=8, w=utils.WIDTH/3, x=2*utils.WIDTH/3, y=0),
                                         datasource=DATASOURCE
                                         )
def gpu():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="avg(resources_assigned_ngpus::float/resources_available_ngpus::float) as pbs, resources_available_gpu_model",
           where="AND resources_available_ngpus != '0'",
           groupby=", resources_available_gpu_model"
           ))],
           title="GPU Allocated by type",
           unit=PERCENT_UNIT_FORMAT,
           gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=0, y=0),
           datasource=DATASOURCE
    )

def cpu():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="avg(resources_assigned_ncpus::float/resources_available_ncpus::float)"
           ))],
           title="CPU Allocated",
           unit=PERCENT_UNIT_FORMAT,
           gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=utils.WIDTH/3, y=0),
           datasource=DATASOURCE
    )

def mem():
    return utils.getTimeSeries(queries=[
        SqlTarget(rawSql=buildQuery(
           select="avg(resources_assigned_mem::float/resources_available_mem::float)",
           where=" AND resources_assigned_mem ~ '^\\d+$'",
           ))],
           title="Memory Allocated",
           unit=PERCENT_UNIT_FORMAT,
           gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH/3, x=2*utils.WIDTH/3, y=0),
           datasource=DATASOURCE
    )

def dashboard():
    overview = RowPanel(
        title = "Overview",
        collapsed = True,
        panels=[*availUtil(), queSize()],
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH, x=0, y=0)
    )

    resources = RowPanel(
        title = "Resources",
        collapsed = True,
        panels=[gpu(), cpu(), mem()],
        gridPos=GridPos(h=utils.HEIGHT, w=utils.WIDTH, x=0, y=utils.HEIGHT)
    )

    return Dashboard(
        title="CasperTest",
        description="Casper dashboard",
        time=utils.INTERVAL,
        refresh='1m',
        sharedCrosshair=True,
        tags=[
            'generated',
            'casper'
        ],
        timezone="browser",
        panels=[ 
            overview,
            resources
        ],
    ).auto_panel_ids()
