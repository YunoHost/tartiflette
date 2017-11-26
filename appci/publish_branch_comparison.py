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

template_path = "./templates/branch_compare.html"

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

    data = { "ci_branches": ci_branches,
           }

    # Sort apps according to level, number of successfull test, name
    def level(test_results):
        if not test_results:
            return -1
        if "level" in test_results and test_results["level"]:
            return test_results["level"]
        return 0

    def compare_levels(a, b):
        if a > b:
            return '+'
        if a < b:
            return '-'
        else:
            return '='

    data["apps"] = []
    for app in apps:
        all_test_results = json.loads(open("data/" + app).read())
        all_levels = [ level(all_test_results[ci_branch]) for ci_branch, _ in ci_branches ]
        data["apps"].append((app, all_levels))

    data["apps"] = sorted(data["apps"], key=lambda a: -a[1][0])

    # Generate the output using the template
    result = t.render(data=data, convert=shell_to_html, shell_css=shell_css)

    output_path = os.path.join(output_dir, "appci_branch_compare.html")
    open(output_path, "w").write(result)

