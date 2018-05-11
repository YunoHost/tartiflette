import requests
import json
import datetime
import os

class UnlistedApps():

    def find_unlisted_apps():


        official = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/official.json").text)
        community = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/community.json").text)

        official_apps = [ os.path.basename(app["url"]) for app in official.values() ]
        community_apps = [ os.path.basename(app["url"]) for app in community.values() ]

        apps = []

        for i in range(0,7):

            print("Page " + str(i) + " ... ")
            r = requests.get("https://api.github.com/search/repositories?q=_ynh&sort=updated&per_page=100&page="+str(i))
            assert r.status_code == 200
            j = json.loads(r.text)
            print(str(len(j["items"])) + " items ")
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

                apps.append(app)

        apps = sorted(apps, key=lambda x: x["updated_days_ago"])

        for app in apps:
            if app["updated_days_ago"] > 100:
                continue
            print(app["name"] + " ... " + app["url"] + " ... " + str(app["updated_days_ago"]))

        with open('apps.json', 'w') as f:
            json.dump(apps, f)


def githubDateToDaysAgo(date):
    now = datetime.datetime.now()
    date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    return (now - date).days


UnlistedApps.find_unlisted_apps()

