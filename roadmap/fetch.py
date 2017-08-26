#!/usr/bin/python3

import requests
import json

roadmaps = { "2.7": 15, "3.0": 14, "3.1": 13 }

def get_roadmapissues():

    for roadmap, id in roadmaps.items():

        issues = requests.get("https://dev.yunohost.org/issues.xml?fixed_version_id="+str(id)+"&status_id=*&limit=100", verify=False)

        with open("data/raw_"+roadmap+"_issues.xml", "w") as f:
            f.write(issues.text)

get_roadmapissues()
