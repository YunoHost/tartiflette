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

        applevel = appdata.split("\n")[1][0]
        appdata = appdata.split("\n")[0]
        data["level"] = applevel

        for c in appdata:
            if c == "0":
                s = "danger"
            elif c == "1":
                s = "success"
            else:
                s = "unknown"

            data["statuses"].append(s)

        apps.append(data)

    apps.sort(key=lambda a: a["level"], reverse=True)

    with open("apps.json", "w") as f: 
        json.dump(apps, f)

main()

