#!/usr/bin/python3

import datetime
import glob
import os
import json
import requests


def githubDateToDaysAgo(date):
    now = datetime.datetime.now()
    date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    return (now - date).days

official = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/official.json").text)
community = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/community.json").text)

official_apps = [ os.path.basename(app["url"]) for app in official.values() ]
community_apps = [ os.path.basename(app["url"]) for app in community.values() ]

unlisted_apps = []

for f in glob.glob("data/*.json"):

    j = json.loads(open(f).read())

    for item in j["items"]:
        app = {
            "name": item["name"],
            "url": item["html_url"],
            "owner": item["owner"]["login"],
            "description": item["description"],
            "updated_days_ago": githubDateToDaysAgo(item["updated_at"])
        }

        if str(item["size"]) == "0":
            continue

        if not app["name"].endswith("_ynh"):
            continue

        if app["name"] in official_apps or app["name"] in community_apps:
            continue

        app["name"] = app["name"].replace("_ynh", "")
        
        unlisted_apps.append(app)

unlisted_apps = sorted(unlisted_apps, key=lambda x: x["updated_days_ago"])

#for app in unlisted_apps:
#        print("%s    %s               %s      %s" % (str(app["updated_days_ago"]),
#                                                    app["name"],
#                                                    app["owner"],
#                                                    app["description"]))
summary = {}
summary["unlisted_apps"] = unlisted_apps
 
with open("summary.json", "w") as f:
    f.write(json.dumps(summary))

