#!/usr/bin/env python3

import datetime
import requests
import json
from functools import partial

import sys
sys.path.insert(0, '../..')
from settings import GITHUB_USER, GITHUB_TOKEN

MAINTENANCE_PING_BODY=open("./maintenance_ping_body").read().strip()
UNMAINTAINED_WARNING=open("./unmaintained_warning").read().strip()

def get_github(uri):
    with requests.Session() as s:
        s.headers.update({"Authorization": "token {}".format(GITHUB_TOKEN)})
        r = s.get("https://api.github.com" + uri)

    #assert r.status_code == 200, "Couldn't get {uri} . Reponse : {text}".format(uri=uri, text=r.text)
    j = json.loads(r.text)
    return j

def github_date_to_days_ago(date):
    now = datetime.datetime.now()
    date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    return (now - date).days

def get_issues(repo):
    return get_github("/repos/{repo}/issues".format(repo=repo))

def get_active_maintenance_ping(issues):

    for issue in issues:
        if issue["title"].startswith("[Maintenance ping]"):
            if issue["state"] == "open":
                issue["created_days_ago"] = github_date_to_days_ago(issue["created_at"])
                return issue

    return None


def get_old_maintenance_ping(issues):

    for issue in issues:
        if issue["title"].startswith("[Maintenance ping]"):
            if issue["state"] == "closed":
                issue["updated_days_ago"] = github_date_to_days_ago(issue["updated_at"])
                return issue

    return None


def get_commit_days_ago(repo, branch):

    ref = get_github("/repos/{repo}/git/refs/heads/{branch}".format(repo=repo, branch=branch))
    if not "object" in ref:
        return 99999

    sha = ref["object"]["sha"]
    github_date = get_github("/repos/{repo}/commits/{sha}".format(repo=repo, sha=sha))["commit"]["author"]["date"]

    return github_date_to_days_ago(github_date)


def create_maintenance_ping(repo):
    api_url = "https://api.github.com/repos/{repo}/issues".format(repo=repo)

    issue = { "title": "[Maintenance ping] Is this app still maintained ?",
              "body": MAINTENANCE_PING_BODY
            }

    with requests.Session() as s:
        s.headers.update({"Authorization": "token {}".format(GITHUB_TOKEN)})
        s.post(api_url, json.dumps(issue))

def warn_unmaintained_if_needed(repo, issue):

    issue_id = issue["number"]
    comments = get_github("/repos/{repo}/issues/{id}/comments".format(repo=repo, id=issue_id))
    existing_warning = [ c for c in comments if c["user"]["login"] == GITHUB_USER
                                             and c["body"].startswith(UNMAINTAINED_WARNING[:20]) ]
    # Nothing to do if there's already a warning about unmaintenained status...
    if existing_warning:
        return

    # Otherwise, post a comment
    api_url = "https://api.github.com/repos/{repo}/issues/{id}/comments" \
              .format(repo=repo, id=issue_id)
    comment = { "body": UNMAINTAINED_WARNING }
    with requests.Session() as s:
        s.headers.update({"Authorization": "token {}".format(GITHUB_TOKEN)})
        s.post(api_url, json.dumps(comment))


def get_status_and_todo(repo):

    # (Get issues of repo)
    issues = get_issues(repo)

    # Is a maintenance ping already opened ?
    active_maintenance_ping = get_active_maintenance_ping(issues)

    if active_maintenance_ping:
        # since more than 15 days ?
        if active_maintenance_ping["created_days_ago"] > 15:
            # yes - > unmaintained !
            # -> post a comment if not already done
            return ("unmaintained", partial(warn_unmaintained_if_needed,
                                           issue=active_maintenance_ping))
        else:
            # no - > maintained ! (but status being questionned)
            return ("maintained?", None)

    # Commit in master or testing in last 18 months ?
    if get_commit_days_ago(repo, "master")  < 18*30 \
    or get_commit_days_ago(repo, "testing") < 18*30:
        # ok, maintained
        return ("maintained", None)

    # Maintainenance status is now being questionned...
    # Was there a (now closed) maintenance ping in the last 6 months ?
    old_maintenance_ping = get_old_maintenance_ping(issues)
    if old_maintenance_ping and old_maintenance_ping["update_days_ago"] < 6*30:
        # Yes - > ok, maintained
        return ("maintained", None)
    else:
        # No - > Gotta create a maintenance ping ! (but still considered maintained)
        return ("maintained?", create_maintenance_ping)

def get_apps_to_check():

    official="https://raw.githubusercontent.com/YunoHost/apps/master/official.json"
    community="https://raw.githubusercontent.com/YunoHost/apps/master/community.json"

    raw_apps = []
    raw_apps += json.loads(requests.get(official).text).values()
    raw_apps += json.loads(requests.get(community).text).values()

    return [ app["url"].replace("https://github.com/","") \
            for app in raw_apps \
            if app["state"] in ["validated", "working", "inprogress"] ]


def main():

    monitored_apps = get_apps_to_check()

    status = {}
    todo = {}

    # For each monitored app :
    for app in monitored_apps:

        print("Checking {} ...".format(app))

        try:
            status[app], todo[app] = get_status_and_todo(app)
        except:
            continue

    to_ping = [ app for app in monitored_apps if status[app] == "maintained?" ]
    print("To ping :")
    print(len(to_ping))
    print("--------")
    for app in to_ping:
        print(app)
        #todo[app](app)

main()
