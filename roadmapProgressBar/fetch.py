#!/usr/bin/python3

import requests
import json

def get_roadmapissues():

    roadmapissues = requests.get("https://dev.yunohost.org/issues.xml?fixed_version_id=11&status_id=*&limit=100")


    with open("data/raw_roadmapissues.xml", "w") as f:
        f.write(roadmapissues.text)

get_roadmapissues()
