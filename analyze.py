#!/usr/bin/python3

import json
import datetime

repos = ["yunohost", "yunohost-admin", "SSOwat", "moulinette", "doc", "ynh-dev",
        "apps", "CI_package_check", "example_ynh", "package_linter", "Simone",
        "project-organization", "build.yunohost.org", "dynette", "YunoPorts",
        "rebuildd", "cd_build", "install_script"]


prs = {}


def githubDateToDaysAgo(date):
    now = datetime.datetime.now()
    date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    return (now - date).days


def isPRDying(pr):
    return (pr["createdDaysAgo"] > 60 and pr["updatedDaysAgo"] > 30)


def priority(pr):
    if   "important" in pr["labels"]:
        base_priority = 100
    elif "opinion needed" in pr["labels"]:
        base_priority = 50
    elif "work needed" in pr["labels"]:
        base_priority = -50
    elif "postponed" in pr["labels"]:
        base_priority = -100
    elif "inactive" in pr["labels"]:
        base_priority = -100
    else:
        base_priority = 0

    if "dying" in pr["labels"] and base_priority > -100:
        base_priority += 5

    return base_priority


def main():

    for repo in repos:

        print("Analyzing %s ..." % repo)

        with open("data/%s.json" % repo, "r") as f:
            j = json.loads(f.read())

        for issue in j:

            # Ignore non-pullrequest issues
            if "pull_request" not in issue.keys():
                continue

            pr = {
               "repo":    repo,
               "title":   issue["title"],
               "labels":  [label["name"] for label in issue["labels"]],
               "id":      "%s-%s" % (repo, issue["number"]),
               "createdDaysAgo": githubDateToDaysAgo(issue["created_at"]),
               "updatedDaysAgo": githubDateToDaysAgo(issue["updated_at"]),
               "url":     issue["pull_request"]["html_url"]
            }

            if len(pr["title"]) > 53:
                pr["title"] = pr["title"][0:50] + "..."

            if isPRDying(pr):
                pr["labels"].append("dying")
            pr["priority"] = priority(pr)

            prs[pr["id"]] = pr

    prs_sorted = sorted(prs.keys(), key=lambda x: (prs[x]["priority"],
        prs[x]["createdDaysAgo"]), reverse=True )

    summary = []

    for name in prs_sorted:
        summary.append(prs[name])

    with open("summary.json", "w") as f:
        f.write(json.dumps(summary))


main()
