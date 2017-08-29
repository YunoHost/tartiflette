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

        if len(appdata.split("\n")) != 2:
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

    with open("apps.json", "w") as f: 
        json.dump(apps, f)

main()

