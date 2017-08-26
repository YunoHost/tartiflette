#!/usr/bin/python3

import os
import json

from jinja2 import Template
from ansi2html import Ansi2HTMLConverter
from ansi2html.style import get_styles

###############################################################################

output_dir = "../www/"

template_path = os.path.join(output_dir,"template_appci.html")
output_path   = os.path.join(output_dir,"appci.html")

summary_path = os.path.join("./", "summary.json")

###############################################################################

conv = Ansi2HTMLConverter()
shell_css = "\n".join(map(str, get_styles(conv.dark_bg, conv.scheme)))

def shell_to_html(shell):
    return conv.convert(shell, False)

###############################################################################

if __name__ == '__main__':

    # Fetch the list of all reports, sorted in reverse-chronological order

    #summary = json.load(open(summary_path))


    summary = { "testnames" : ["Package linter","Installation","Deleting","Installation in a sub path","Deleting from a sub path","Installation on the root","Deleting from root","Upgrade","Installation in private mode","Installation in public mode","Multi-instance installations","Malformed path","Port already used","Backup","Restore","Change URL"]}

    summary["apps"] = json.loads(open("apps.json").read())

    # Generate the output using the template

    template = open(template_path, "r").read()
    t        = Template(template)
 
    result = t.render(data=summary, convert=shell_to_html, shell_css=shell_css)

    open(output_path, "w").write(result)

    print("Done.")
