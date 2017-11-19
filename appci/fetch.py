import os
import time
import json
import requests
import dateutil.parser

tests = [ "Package linter",
          "Installation",
          "Deleting",
          "Upgrade",
          "Backup",
          "Restore",
          "Change URL",
          "Installation in a sub path",
          "Deleting from a sub path",
          "Installation on the root",
          "Deleting from root",
          "Installation in private mode",
          "Installation in public mode",
          "Multi-instance installations",
          "Malformed path",
          "Port already used" ]


def main():

    apps = fetch_applist()

    ci_results = {}
    for appname, appinfo in sorted(apps.items()):
        print "==> %s" % appname
        ci_results[appname] = {}
        for ci_branch in ["stable", "testing", "unstable", "arm"]:
            print "   > Fetching results for CI branch %s" % ci_branch
            raw_console = get_raw_ci_output(appinfo, ci_branch)
            if raw_console is None:
                ci_results[appname][ci_branch] = None
                continue

            test_results = analyze_ci_output(raw_console)
            ci_results[appname][ci_branch] = test_results

        with open('data/%s' % appname, 'w') as f:
            json.dump(ci_results[appname], f)

def fetch_applist():

    official = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/official.json").text)
    community = json.loads(requests.get("https://raw.githubusercontent.com/YunoHost/apps/master/community.json").text)

    for appname, appinfo in official.items():
        appinfo["ci_name"] = ci_name(appinfo, official=True)

    for appname, appinfo in community.items():
        # Ignore apps that are not declared as 'working'
        if appinfo["state"] != "working":
            del community[appname]
        appinfo["ci_name"] = ci_name(appinfo, official=False)

    return dict(official.items() + community.items())


def ci_name(app, official):
    ci_name = os.path.basename(app["url"]).replace("_ynh", "")
    ci_name += " (Official)" if official else " (Community)"
    return ci_name


def get_raw_ci_output(app, ci_branch="stable"):

    assert ci_branch in [ "stable", "testing", "unstable", "stretch", "arm", "apptesting" ]

    ci_server="ci-apps.yunohost.org"
    ci_test_name = app["ci_name"]

    if ci_branch == "stable":
        # Keep default
        pass
    if ci_branch == "testing":
        ci_test_name += " (testing)"
    if ci_branch == "unstable":
        ci_test_name += " (unstable)"
    if ci_branch == "arm":
        ci_test_name += " (~ARM~)"
    if ci_branch == "stretch":
        ci_server = "???"
    if ci_branch == "apptesting":
        # Not supported yet
        return ""

    console_url = "https://%s/jenkins/job/%s/lastBuild/consoleText" % (ci_server, ci_test_name)

    print console_url

    # FIXME : should force ipv4 here?
    r = requests.get(console_url)
    return r.text.split('\n') if r.status_code == 200 else None

def analyze_ci_output(raw_console):

    tests_results = {}

    # Find individual tests results
    for test in tests:
        # A test can have been done several times... We grep all lines
        # corresponding to this test
        test_results = [ line for line in raw_console if line.startswith(test+":") ]

        # For each line corresponding to this test, if there's at least one
        # failed, it means this test failed
        if [ line for line in test_results if "FAIL" in line ]:
            tests_results[test] = False
        # Otherwise, if there's at least one success, it means this test
        # succeeded
        elif [ line for line in test_results if "SUCCESS" in line ]:
            tests_results[test] = True
        # Otherwise, this means it has not been evaluated
        else:
            tests_results[test] = None

    # Find level
    level = 0
    for line in raw_console:
        if line.startswith('Level of this application:'):
            try:
                level = int(line.replace('Level of this application:', '').split()[0])
            except:
                pass # Sorry Bram :<

    # Find date
    date = None
    for previous_line, line in zip(raw_console, raw_console[1:]):
      if line == "Test finished.":
          # Get date from previous line and parse it into a timestamp
          date = previous_line
          try:
            date = int(time.mktime(dateutil.parser.parse(date).timetuple()))
          except:
            # Meh
            date = None

    results = {
        "tests": tests_results,
        "level": level,
        "date": date
    }

    return results

main()
