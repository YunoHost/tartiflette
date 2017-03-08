#!/usr/bin/python3

import os
import json

from jinja2 import Template
from ansi2html import Ansi2HTMLConverter
from ansi2html.style import get_styles

###############################################################################

output_dir = "./www/"

template_path = os.path.join(output_dir,"template.html")
output_path   = os.path.join(output_dir,"index.html")

summary_path = os.path.join("./", "summary.json")

###############################################################################

conv = Ansi2HTMLConverter()
shell_css = "\n".join(map(str, get_styles(conv.dark_bg, conv.scheme)))

def shell_to_html(shell):
    return conv.convert(shell, False)

###############################################################################

if __name__ == '__main__':

    # Fetch the list of all reports, sorted in reverse-chronological order

    pr_list = json.load(open(summary_path))

    # Generate the output using the template

    template = open(template_path, "r").read()
    t        = Template(template)
 
    result = t.render(data=pr_list, convert=shell_to_html, shell_css=shell_css)

    open(output_path, "w").write(result)

    print("Done.")
