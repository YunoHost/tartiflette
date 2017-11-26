#!/usr/bin/python2.7

import os
import json
import glob

from jinja2 import Template
from ansi2html import Ansi2HTMLConverter
from ansi2html.style import get_styles
from common import tests, ci_branches

###############################################################################

output_dir = "../www/"
template_path = "./templates/app.html"

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

    for app in apps:

        results = json.loads(open("data/" + app).read())

        # Meh
        try:
            level = "level" + str(int(results["stable"]["level"]))
        except:
            level = "unknown"

        os.symlink("%s/badges/%s.svg" % (os.getcwd(), level),
                   "../www/integration/%s.svg" % app)

        data = {
            "appname": app,
            "ci_branches": ci_branches,
            "tests": tests,
            "results": results,
            "result_to_class": { None:"unknown", False:"danger", True:"success" }
        }

        # Generate the output using the template
        result = t.render(data=data, convert=shell_to_html, shell_css=shell_css)

        output_path = os.path.join(output_dir, "appci", "app", "%s.html" % app)
        open(output_path, "w").write(result)

