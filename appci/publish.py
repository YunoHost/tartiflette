#!/usr/bin/python2.7
import os
import glob
from publish_apps import main as publish_apps
from publish_branches import main as publish_branches

def main():
    for link in glob.glob("../www/integration/*.svg"):
        os.unlink(link);
    os.symlink("%s/badges/unknown.svg" % os.getcwd(),
               "../www/integration/unknown.svg")

    publish_branches()
    publish_apps()

if __name__ == '__main__':
    main()

