#!/usr/bin/python3

import os
import json
import glob

from jinja2 import Template
from ansi2html import Ansi2HTMLConverter
from ansi2html.style import get_styles

###############################################################################

output_dir = "../www/"

template_path = os.path.join(output_dir,"template_appci_perapp.html")

tests = [ "Package linter",
          "Installation",
          "Deleting",
          "Upgrade",
          "Backup",
          "Restore",
          "Change URL",
          "Installation in a sub path",
          "Deleting from a sub path",
          "Installation on the root",
          "Deleting from root",
          "Installation in private mode",
          "Installation in public mode",
          "Multi-instance installations",
          "Malformed path",
          "Port already used" ]

ci_branches = [ ("stable", "Stable (x86)"),
                ("arm", "Stable (ARM)"),
                ("testing", "Testing"),
                ("unstable", "Unstable") ]

###############################################################################

conv = Ansi2HTMLConverter()
shell_css = "\n".join(map(str, get_styles(conv.dark_bg, conv.scheme)))

def shell_to_html(shell):
    return conv.convert(shell, False)

###############################################################################

if __name__ == '__main__':

    # Load the template
    template = open(template_path, "r").read()
    t        = Template(template)

    apps = [ file_.replace("data/", "") for file_ in glob.glob("data/*") ]

    for app in apps:

        print app

        data = {
            "appname": app,
            "ci_branches": ci_branches,
            "tests": tests,
            "results": json.loads(open("data/" + app).read()),
            "result_to_class": { None:"unknown", False:"danger", True:"success" }

        }
        # Generate the output using the template
        result = t.render(data=data, convert=shell_to_html, shell_css=shell_css)

        output_path = os.path.join(output_dir,"ciperapp", "%s.html" % app)
        open(output_path, "w").write(result)

