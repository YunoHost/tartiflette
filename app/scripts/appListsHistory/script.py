import toml
import json
import os
import sys
import inspect
from datetime import datetime

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
appdir = os.path.abspath(currentdir + "../../../../")
sys.path.insert(0, appdir)

from app import db, create_app
from app.models.appcatalog import App
app_ = create_app()


def _time_points_until_today():

    year = 2017
    month = 1
    day = 1
    today = datetime.today()
    date = datetime(year, month, day)

    while date < today:
        yield date

        day += 14
        if day > 15:
            day = 1
            month += 1

        if month > 12:
            month = 1
            year += 1

        date = datetime(year, month, day)


time_points_until_today = list(_time_points_until_today())


def get_lists_history():

    os.system("rm -rf ./.work")
    os.system("git clone https://github.com/YunoHost/apps ./.work/apps")

    for t in time_points_until_today:
        print(t.strftime("%b %d %Y"))

        # Fetch repo at this date
        cmd = 'cd ./.work/apps; git checkout `git rev-list -1 --before="%s" master`'
        os.system(cmd % t.strftime("%b %d %Y"))

        if t < datetime(2019, 4, 4):
            # Merge community and official
            community = json.loads(open("./.work/apps/community.json").read())
            official = json.loads(open("./.work/apps/official.json").read())
            for key in official:
                official[key]["state"] = "official"
            merged = {}
            merged.update(community)
            merged.update(official)
        else:
            try:
                merged = toml.loads(open("./.work/apps/apps.toml").read())
            except:
                try:
                    merged = json.loads(open("./.work/apps/apps.json").read())
                except:
                    pass

        # Save it
        json.dump(merged, open('./.work/merged_lists.json.%s' % t.strftime("%y-%m-%d"), 'w'))


def make_count_summary():

    states = ["official", "working", "inprogress", "notworking"]
    history = []

    last_time_point = time_points_until_today[-1]
    json_at_last_time_point = json.loads(open("./.work/merged_lists.json.%s" % last_time_point.strftime("%y-%m-%d")).read())
    relevant_apps_to_track = [app
                              for app, infos in json_at_last_time_point.items()
                              if infos.get("state") in ["working", "official"]]
    history_per_app = {app: [] for app in relevant_apps_to_track}

    for d in time_points_until_today:

        print("Analyzing %s ..." % d.strftime("%y-%m-%d"))

        # Load corresponding json
        j = json.loads(open("./.work/merged_lists.json.%s" % d.strftime("%y-%m-%d")).read())
        d_label = d.strftime("%b %d %Y")

        summary = {}
        summary["date"] = d_label
        for state in states:
            summary[state] = len([k for k, infos in j.items() if infos.get("state") == state])

        for level in range(0, 10):
            summary["level-%s" % level] = len([k for k, infos in j.items()
                                               if infos.get("state") in ["working", "official"]
                                               and infos.get("level", None) == level])

        history.append(summary)

        for app in relevant_apps_to_track:

            infos = j.get(app, {})

            if not infos or infos.get("state") not in ["working", "official"]:
                level = -1
            else:
                level = infos.get("level", -1)
                try:
                    level = int(level)
                except:
                    level = -1

            history_per_app[app].append({
                "date": d_label,
                "level": level
            })

    json.dump(history, open('count_history.json', 'w'))

    os.system("mkdir -p per_app/")
    for app in relevant_apps_to_track:
        json.dump(history_per_app[app], open('per_app/history_%s.json' % app, 'w'))

    with app_.app_context():
        for app in relevant_apps_to_track:
            update_catalog_stats(app, history_per_app[app])

        db.session.commit()

def make_news():

    news_per_date = {d.strftime("%b %d %Y"): {"broke": [], "repaired": [], "removed": [], "added": []} for d in time_points_until_today}
    previous_j = {}

    def level(infos):
        lev = infos.get("level")
        if lev is None or (isinstance(lev, str) and not lev.isdigit()):
            return -1
        else:
            return int(lev)


    for d in time_points_until_today:
        d_label = d.strftime("%b %d %Y")

        print("Analyzing %s ..." % d.strftime("%y-%m-%d"))

        # Load corresponding json
        j = json.loads(open("./.work/merged_lists.json.%s" % d.strftime("%y-%m-%d")).read())

        apps_current = set(k for k, infos in j.items() if infos.get("state") in ["working", "official"] and level(infos) != -1)
        apps_current_good = set(k for k, infos in j.items() if k in apps_current and level(infos) > 4)
        apps_current_broken = set(k for k, infos in j.items() if k in apps_current and level(infos) <= 4)

        apps_previous = set(k for k, infos in previous_j.items() if infos.get("state") in ["working", "official"] and level(infos) != -1)
        apps_previous_good = set(k for k, infos in previous_j.items() if k in apps_previous and level(infos) > 4)
        apps_previous_broken = set(k for k, infos in previous_j.items() if k in apps_previous and level(infos) <= 4)

        news = news_per_date[d_label]
        for app in set(apps_previous_good & apps_current_broken):
            news["broke"].append((app, j[app]["url"]))
        for app in set(apps_previous_broken & apps_current_good):
            news["repaired"].append((app, j[app]["url"]))
        for app in set(apps_current - apps_previous):
            news["added"].append((app, j[app]["url"]))
        for app in set(apps_previous - apps_current):
            news["removed"].append((app, previous_j[app]["url"]))

        previous_j = j

    json.dump(news_per_date, open('news.json', 'w'))


def update_catalog_stats(app, history):

    print(app)
    try:
        app_in_db = App.query.filter_by(name=app).first_or_404()
    except:
        return

    app_in_db.long_term_good_quality = len([d for d in history[-24:] if d["level"] > 5]) > 0.90 * 24
    app_in_db.long_term_broken = history[-1]["level"] == 0 and len([d for d in history[-24:] if d["level"] >= 0 and d["level"] <= 2]) > 12

    db.session.add(app_in_db)


get_lists_history()
make_count_summary()
make_news()
