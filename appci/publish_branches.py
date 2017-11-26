#!/usr/bin/python3

import os
import json
import glob

from jinja2 import Template
from ansi2html import Ansi2HTMLConverter
from ansi2html.style import get_styles

from common import tests, ci_branches

###############################################################################

output_dir = "../www/"

template_path = "./templates/branch.html"

###############################################################################

conv = Ansi2HTMLConverter()
shell_css = "\n".join(map(str, get_styles(conv.dark_bg, conv.scheme)))

def shell_to_html(shell):
    return conv.convert(shell, False)

###############################################################################

def main():

    # Load the template
    template = open(template_path, "r").read()
    t        = Template(template)

    apps = [ file_.replace("data/", "") for file_ in glob.glob("data/*") ]

    for branch in ci_branches:
        branch_id = branch[0]

        data = { "ci_branch": branch,
                 "tests": tests,
                 "result_to_class": { None: "unknown",
                                      False: "danger",
                                      True: "success" }
               }

        data["apps"] = []
        for app in apps:
            data["apps"].append((app, json.loads(open("data/" + app).read())[branch_id]))

        # Sort apps according to level, number of successfull test, name
        def level(app):
            test_results = app[1]
            if not test_results:
                return -2
            if "level" in test_results:
                l = test_results["level"]
                return l if not l is None else -1
            return -1

        def test_score(app):
            test_results = app[1]
            if not test_results or "tests" not in test_results:
                return -1

            score = 0
            for test, r in test_results["tests"].items():
                if r == True:
                    score += 1
                elif r == False:
                    score -= 1
            return score

        data["apps"] = sorted(data["apps"], key=lambda a: (-level(a), -test_score(a)))

        summary_per_level = []
        summary_per_level.append(("Untested", len([ a for a in data["apps"] if level(a) == -1 ])))
        for l in range(0, 8):
            summary_per_level.append(("Level %s" % l, len([ a for a in data["apps"] if level(a) == l ])))
        data["summary_per_level"] = summary_per_level

        # Generate the output using the template
        result = t.render(data=data, convert=shell_to_html, shell_css=shell_css)

        output_path = os.path.join(output_dir, "appci", "branch", "%s.html" % branch_id)
        open(output_path, "w").write(result)

