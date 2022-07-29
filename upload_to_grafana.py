from grafanalib.core import Dashboard
from grafanalib._gen import DashboardEncoder
import json
import requests
from os import getenv


def _get_dashboard_json(dashboard, overwrite=False, message="Updated by grafanlib"):
    '''
    get_dashboard_json generates JSON from grafanalib Dashboard object
    :param dashboard - Dashboard() created via grafanalib
    '''

    # grafanalib generates json which need to pack to "dashboard" root element
    return json.dumps(
        {
            "dashboard": dashboard.to_json_data(),
            "overwrite": overwrite,
            "message": message,
            "folderUid": "E9XLpYr7z"
        }, sort_keys=True, indent=2, cls=DashboardEncoder)


def _upload_dashboard(json, server, api_key, verify=True):
    '''
    upload_to_grafana tries to upload dashboard to grafana and prints response
    :param json - dashboard json generated by grafanalib
    :param server - grafana server name
    :param api_key - grafana api key with read and write privileges
    '''

    headers = {'Authorization': f"Bearer {api_key}", 'Content-Type': 'application/json'}
    r = requests.post(f"https://{server}/api/dashboards/db", data=json, headers=headers, verify=verify)
    # TODO: add error handling
    print(f"{r.status_code} - {r.content}")


def upload(dashboard):
    grafana_api_key = getenv("GRAFANA_API_KEY")
    grafana_server = getenv("GRAFANA_SERVER")
    dashboard_json = _get_dashboard_json(dashboard, overwrite=True)
    _upload_dashboard(dashboard_json, grafana_server, grafana_api_key)
