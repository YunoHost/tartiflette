#!/usr/bin/python2

import json
import BeautifulSoup

roadmaps = { "2.6.x": 11, "2.7.x": 13 }

status_filters = {
    "all": None,
    "new": ["New", "Confirmed"],
    "ongoing": ["In Progress"],
    "done": ["Closed", "Resolved", "Rejected"]
}


def parse_issues():

    issues = []

    for roadmap in sorted(roadmaps.keys()):

        soup = BeautifulSoup.BeautifulSoup(open("data/raw_"+roadmap+"_issues.xml").read())

        for issue in soup.issues:
            cleaned_issue = {}
            cleaned_issue["id"]       = issue.id.text
            cleaned_issue["priority"] = issue.priority["name"]
            cleaned_issue["status"]   = issue.status["name"]
            cleaned_issue["type"]     = issue.tracker["name"]
            cleaned_issue["subject"]  = issue.subject.text
            cleaned_issue["roadmap"]  = roadmap
            cleaned_issue["p"]        = priority(cleaned_issue)
           
            issues.append(cleaned_issue)

    issues = sorted(issues, key=lambda x: x["p"], reverse=True )

    return issues


def filtered_issues(issues, roadmap, status_filter=None, type_filter=None):

    issues_filtered = [ issue for issue in issues if issue["roadmap"] == roadmap ]

    if status_filter != None:
        issues_filtered = [ issue for issue in issues_filtered if issue["status"] in status_filter]

    if type_filter != None:
        issues_filtered = [ issue for issue in issues_filtered if issue["type"] == type_filter ]

    return len(issues_filtered)


def priority(issue):

    p = 0
    
    if (issue["type"] == "Bug"):
        p += 5
    if (issue["priority"] == "High"): 
        p += 5
    if (issue["priority"] == "Low"): 
        p -= 5

    if (issue["status"] in status_filters["done"]):
        p -= 50
        if (issue["status"] == "Rejected"):
            p -= 20
        if (issue["status"] == "Closed"):
            p -= 10

    elif (issue["status"] in status_filters["ongoing"]):
        p -= 20
    elif (issue["status"]):
        p += 10

    p -= sorted(roadmaps.keys()).index(issue["roadmap"]) / 10

    return p

def main():

    # Parse issues...
    issues = parse_issues()

    # Build summary
    summary = {}
    for roadmap in roadmaps:
        summary[roadmap] = {}

    # First add issues by status
    for roadmap in roadmaps:
        for status_name, status_filter in status_filters.items():
            summary[roadmap][status_name] = filtered_issues(issues, roadmap, status_filter)

    print summary

    # The compute percent
    for roadmap in roadmaps:
        for status_name, status_filter in status_filters.items():
            if (status_name != "all"):
                n = summary[roadmap][status_name]
                p = float("{0:.1f}".format(100 * n / summary[roadmap]["all"]))
                summary[roadmap][status_name] = (n,p)

    # (Meh)
    summary = { "summary": summary }
    summary["issues"] = issues
     
    # Write summary to json file
    with open("summary.json", "w") as f:
        f.write(json.dumps(summary))


main()

