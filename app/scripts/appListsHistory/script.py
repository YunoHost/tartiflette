
import json
import os
from datetime import datetime
from feedgen.feed import FeedGenerator
import jinja2

state_to_value = { "working":1,
                   "inprogress": 0,
                   "notworking": -1,
                 }

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

        # Merge community and official
        community = json.loads(open("./.work/apps/community.json").read())
        official = json.loads(open("./.work/apps/official.json").read())
        for key in official:
            official[key]["state"] = "official"
        merged = {}
        merged.update(community)
        merged.update(official)

        # Save it
        json.dump(merged, open('./.work/merged_lists.json.%s' % t.strftime("%y-%m-%d"), 'w'))

def diffs():

    # Iterate over pairs of date : (t0,t1), (t1,t2), ...
    dates = time_points_until_today
    for d1, d2 in zip(dates[:-1], dates[1:]):

        print("Analyzing %s ... %s" % (d1.strftime("%y-%m-%d"), d2.strftime("%y-%m-%d")))

        # Load corresponding json
        f1 = json.loads(open("./.work/merged_lists.json.%s" % d1.strftime("%y-%m-%d")).read())
        f2 = json.loads(open("./.work/merged_lists.json.%s" % d2.strftime("%y-%m-%d")).read())

        for key in f1:
            f1[key]["name"] = key

        for key in f2:
            f2[key]["name"] = key

        keys_f1 = set(f1.keys())
        keys_f2 = set(f2.keys())

        removed = [ f1[k] for k in keys_f1 - keys_f2 ]
        added   = [ f2[k] for k in keys_f2 - keys_f1 ]
        keys_inboth  = keys_f1 & keys_f2

        state_changes = []
        level_changes = []
        updates = []
        for key in keys_inboth:

            changes = []

            # FIXME : this mechanism aint relevant anymore since
            # the norm is to use HEAD now...
            commit1 = f1[key].get("revision", None)
            commit2 = f2[key].get("revision", None)
            if commit1 != commit2:
                changes.append("updated")

            state1 = f1[key].get("state", None)
            state2 = f2[key].get("state", None)
            if state1 != state2:
                changes.append(("state", state1, state2))

            level1 = f1[key].get("level", None)
            level2 = f2[key].get("level", None)
            if level1 != level2:
                changes.append(("level", level1, level2))

            if level1 != level2 or state1 != state2:
                level1_value = level1 if level1 else 0
                level2_value = level2 if level2 else 0
                if level1_value < level2_value:
                    changes.append("improvement")
                elif level1_value > level2_value:
                    changes.append("regression")
                else:
                    state1_value = state_to_value.get(state1,-1)
                    state2_value = state_to_value.get(state2,-1)
                    if state1_value < state2_value:
                        changes.append("improvement")
                    elif state1_value > state2_value:
                        changes.append("regression")
                    else:
                        changes.append("same")

            if changes:
                updates.append((f2[key], changes))

        yield { "begin": d1,
                "end": d2,
                "new": sorted(added, key=lambda a:a["name"]),
                "improvements": sorted([a for a in updates if "improvement" in a[1]], key=lambda a:a[0]["name"]),
                "updates": sorted([a for a in updates if "same" in a[1]], key=lambda a:a[0]["name"]),
                "regressions": sorted([a for a in updates if "regression" in a[1]], key=lambda a:a[0]["name"]),
                "removed": sorted(removed, key=lambda a:a["name"]),
              }


def make_rss_feed():

    fg = FeedGenerator()
    fg.id('https://github.com/YunoHost/Apps/')
    fg.title('App Lists news')
    fg.author( {'name':'YunoHost'} )
    fg.language('en')

    for diff in diffs():
        fe = fg.add_entry()
        fe.id('https://github.com/YunoHost/Apps/#'+diff["end"].strftime("%y-%m-%d"))
        fe.title('Changes between %s and %s' % (diff["begin"].strftime("%b %d"), diff["end"].strftime("%b %d")))
        fe.link(href='https://github.com/YunoHost/apps/commits/master/community.json')
        fe.content(jinja2.Template(open("rss_template.html").read()).render(data=diff), type="html")
        fe._FeedEntry__atom_updated = diff["end"]

    print('Changes between %s and %s' % (diff["begin"].strftime("%b %d"), diff["end"].strftime("%b %d")))
    open("tmp.html", "w").write(jinja2.Template(open("rss_template.html").read()).render(data=diff))

    fg.atom_file('atom.xml')

def make_count_summary():

    states = ["official", "working", "inprogress", "notworking"]
    history = []

    per_state = { state: [] for state in states }
    per_level = { "level-%s"%i: [] for i in range(0,8) }

    for d in time_points_until_today:

        print("Analyzing %s ..." % d.strftime("%y-%m-%d"))

        # Load corresponding json
        j = json.loads(open("./.work/merged_lists.json.%s" % d.strftime("%y-%m-%d")).read())
        d_label = d.strftime("%b %d %Y")

        summary = {}
        summary["date"] = d_label
        for state in states:
            summary[state] = len([ k for k, infos in j.items() if infos["state"] == state ])

        for level in range(0,8):
            summary["level-%s"%level] = len([ k for k, infos in j.items() \
                                              if  infos["state"] in ["working", "official"] \
                                              and infos.get("level", None) == level ])

        history.append(summary)

    json.dump(history, open('count_history.json', 'w'))

get_lists_history()
make_rss_feed()
make_count_summary()
