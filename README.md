# Grafana Dashboards
This repo is for version controlling dashboards

Dashboards are programatically created using [grafanalib](https://github.com/weaveworks/grafanalib)

## Setup
- On Cheyenne (can also do this where ever)
```
module load conda
conda create --name grafana
conda activate grafana
conda install python
pip install grafanalib

git clonegit@git.hsg.ucar.edu:shanks/GrafanaDashboards.git
cd grafanaDashboards
```

## Usage
```
module load conda
conda activate grafana
cd grafanaDashboards

git pull
# perform your edits
git add <files you editted>
git commit # write a brief commit message
git push
```

## Updating dashboards in grafana
- Working on automating this so that they stay in sync w/ master branch
- ensure the `upload_to_grafana` method is called with the dashboard to be updated at the end of said dashboards .py file

```
GRAFANA_API_KEY=<get a key from grafana>
GRAFANA_SERVER="grafana.hpc.ucar.edu"
python /path/to/dashboard.py
```
