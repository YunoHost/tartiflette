#!/usr/bin/python3

import requests
import json

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

for repo in get_repos().keys():

    print("Fetching pull requests for %s" % repo)

    issues = requests.get("https://api.github.com/repos/yunohost/%s/issues?per_page=100" % repo)

    with open("data/%s.json" % repo, "w") as f:
        f.write(issues.text)
