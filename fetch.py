#!/usr/bin/python3

import requests

repos = ["yunohost", "yunohost-admin", "SSOwat", "moulinette", "doc", "ynh-dev",
        "apps", "CI_package_check", "example_ynh", "package_linter", "Simone",
        "project-organization", "build.yunohost.org", "dynette", "YunoPorts",
        "rebuildd", "cd_build", "install_script"]


for repo in repos:

    print("Fetching pull requests for %s" % repo)

    issues = requests.get("https://api.github.com/repos/yunohost/%s/issues?per_page=100" % repo)

    with open("./%s.json" % repo, "w") as f:
        f.write(issues.text)
