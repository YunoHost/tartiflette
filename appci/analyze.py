#!/usr/bin/python

import os
import json
import glob


def main():

    apps = []

    for f in glob.glob("data/*"):

        app = f.replace("data/","")
        appdata = open(f).read().strip()

        if appdata == "":
            continue

        data = {}
        data["name"] = app
        data["statuses"] = []

        if len(appdata.split("\n")) != 2 or len(appdata) != 28:
            print "Ignoring %s - bad/unavailable data" % app
            continue

        applevel = appdata.split("\n")[1][0]
        appdata = appdata.split("\n")[0]
        data["level"] = int(applevel)

        statusescore = 0
        for c in appdata:
            if c == "0":
                s = "danger"
                statusescore -= 1
            elif c == "1":
                s = "success"
                statusescore += 1
            else:
                s = "unknown"

            data["statuses"].append(s)

        data["statusescore"] = statusescore


        apps.append(data)

    apps.sort(key=lambda a: (a["level"], a["statusescore"], a["name"]), reverse=True)

    for link in glob.glob("../www/integration/*.svg"):
        os.unlink(link);

    os.symlink("%s/badges/unknown.svg" % os.getcwd(),
               "../www/integration/unknown.svg")

    for app in apps:
        os.symlink("%s/badges/level%s.svg" % (os.getcwd(), app["level"]),
                   "../www/integration/%s.svg" % app["name"])

    with open("apps.json", "w") as f:
        json.dump(apps, f)


main()

