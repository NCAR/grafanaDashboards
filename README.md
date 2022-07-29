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

conda install requests # only needed for uploading dashboards

git clonegit@git.hsg.ucar.edu:shanks/GrafanaDashboards.git
cd grafanaDashboards
```

## Usage
```
# get env setup and updated
module load conda
conda activate grafana

git pull
git branch <new feature branch name>
git checkout <feature branch name>


# perform your edits

# test your updates
./main.py <dashboard filename w/o extension> # ex ./main.py bifrost

# when happy with changes push to repo
git add <files you editted>
git commit # write a brief commit message
git push

# after creating a PR and having it merged
# update env
git pull
git checkout master
git branch -d -r origin/<feature branch name>

# update grafana
export GRAFANA_API_KEY=<get a key from grafana>
export GRAFANA_SERVER="grafana.hpc.ucar.edu"
./main.py
```

## Creating new dashboards
- make a file in the `dashboards` dir
- it _must_ contain a `dashboard()` method which returns a grafanalib `Dashboard` object
- this will automatically be picked up by `main.py` and uploaded


```
```
