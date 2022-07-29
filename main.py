#!/usr/bin/env python3
from upload_to_grafana import upload

import glob
import importlib
import sys

def uploadDashboard(dashboard):
    print(f"Uploading {dashboard} dashboard")
    #  import it so we can run dashboard() on it and update grafana
    d = importlib.import_module(f".{dashboard}", package='dashboards')
    upload(d.dashboard())


def main():
    #  check if trying to only upload a single dashboard
    if len(sys.argv) > 1:
        uploadDashboard(sys.argv[1]) 
        return

    print("Uploading all dashboards")
    for dashboard in glob.iglob('./dashboards/*.py'):
        #  skip __init__.py
        if dashboard[13] == '_':
            continue
        #  remove ./dashboards and .py from string
        dashboardName = dashboard[13:-3]
        uploadDashboard(dashboardName)
    

if __name__ == '__main__':
    main()
