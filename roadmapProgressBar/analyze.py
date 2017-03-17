#!/usr/bin/python3

import json
from bs4 import BeautifulSoup


status_filters = {
        "all": None,
        "new": ["New", "Confirmed"],
        "ongoing": ["In Progress"],
        "done": ["Closed", "Resolved", "Rejected"]
    }

type_filters = {
        "all": None,
        "Bug": "Bug",
        "Feature": "Feature",
        "Improve": "Improvement",
        "Doc": "Documentation"
    }



def parse_issues():

    soup = BeautifulSoup(open("data/raw_roadmapissues.xml").read(), "lxml")

    issues = []

    for issue in soup.issues:
        cleaned_issue = {}
        cleaned_issue["id"]       = issue.id.text
        cleaned_issue["priority"] = issue.priority["name"]
        cleaned_issue["status"]   = issue.status["name"]
        cleaned_issue["type"]     = issue.tracker["name"]

        issues.append(cleaned_issue)

    return issues


def filtered_issues(issues, status_filter=None, type_filter=None):
    
    issues_filtered = issues
    if status_filter != None:
        issues_filtered = [ issue for issue in issues_filtered if issue["status"] in status_filter]

    if type_filter != None:
        issues_filtered = [ issue for issue in issues_filtered if issue["type"] == type_filter ]

    return len(issues_filtered)


def main():

    issues = parse_issues()
    summary = {}

    for type_name, type_filter in type_filters.items():

        summary[type_name] = {}

        for status_name, status_filter in status_filters.items():

            summary[type_name][status_name] = filtered_issues(issues, status_filter,
                    type_filter)

    for type_name, type_filter in type_filters.items():

        for status_name, status_filter in status_filters.items():
        
            if (status_name != "all"):

                n = summary[type_name][status_name]
                p = float("{0:.1f}".format(100 * n / summary[type_name]["all"]))
                summary[type_name][status_name] = (n,p)

        if (type_name != "all"):
            n = summary[type_name]["all"]
            p = float("{0:.1f}".format(100 * n / summary["all"]["all"]))
            summary[type_name]["all"] = (n,p) 
        


    with open("summary.json", "w") as f:
        f.write(json.dumps(summary))


main()

