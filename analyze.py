#!/usr/bin/python3

import json
import datetime

prs = {}

def get_teams():

    with open("repos.json", "r") as f:
        return json.loads(f.read()).keys()


def get_repos():

    repos_by_name = {}

    with open("repos.json", "r") as f:
        repos_by_team = json.loads(f.read())

    for team, team_repos in repos_by_team.items():
        for repo in team_repos:
            if repo not in repos_by_name.keys():
                repos_by_name[repo] = [team]
            else:
                repos_by_name[repo].append(team)

    return repos_by_name


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
    elif "postponed" in pr["labels"]:
        base_priority = -100
    elif "inactive" in pr["labels"]:
        base_priority = -100
    else:
        base_priority = 0

    if "work needed" in pr["labels"]:
        base_priority += -5

    if "dying" in pr["labels"] and base_priority > -100:
        base_priority += 5

    return base_priority


def main():

    for repo, teams in get_repos().items():

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
               "url":     issue["pull_request"]["html_url"],
               "teams":   teams
            }

            if isPRDying(pr):
                pr["labels"].append("dying")
            pr["priority"] = priority(pr)

            prs[pr["id"]] = pr

    prs_sorted = sorted(prs.keys(), key=lambda x: (prs[x]["priority"],
        prs[x]["createdDaysAgo"]), reverse=True )

    summary = {}
    
    summary["teams"] = {}
    summary["teams"]["all"] = len([pr for pr in prs.values() if pr["priority"] >= -50])
    for team in get_teams():
        summary["teams"][team] = len([pr for pr in prs.values()
                 if team in pr["teams"] and pr["priority"] >= -50])

    summary["prs"] = []
    for name in prs_sorted:
        summary["prs"].append(prs[name])

    with open("summary.json", "w") as f:
        f.write(json.dumps(summary))


main()
