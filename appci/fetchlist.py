
import os
import json
import requests

official = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/official.json").text)
community = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/community.json").text)

official_apps = [ os.path.basename(app["url"]).replace("_ynh", "")+" (Official)" for app in official.values() ]
community_apps = [ os.path.basename(app["url"]).replace("_ynh", "")+" (Community)" for app in community.values() if app["state"] == "working" ]

for app in official_apps:
    print app
for app in community_apps:
    print app
