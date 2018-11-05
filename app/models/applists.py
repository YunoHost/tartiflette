import re
import os
import time
import json
import requests
import datetime

from .. import db


class AppList(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(128), nullable=False)
    state_for_ci = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return '<AppList %r>' % self.name

    def init():
        yield AppList(name='official',
                      url="https://app.yunohost.org/official.json",
                      state_for_ci='validated')
        yield AppList(name='community',
                      url="https://app.yunohost.org/community.json",
                      state_for_ci='working')

    def update():

        applists = AppList.query.all()
        for applist in applists:
            applist.update_list()

    def update_list(self):

        g = Github()

        raw_apps = json.loads(requests.get(self.url).text).values()
        apps = [ app for app in raw_apps ]

        for app in apps:

            app['url'] = app["git"]["url"].strip('/')
            name = os.path.basename(app["url"]).replace("_ynh", "")

            # Try to find an app for this name
            known_app = App.query.filter_by(name=name).first()

            # If this app is not already registered...
            if not known_app:
                print("Adding new app {}".format(name))
                known_app = App(name=name,
                                repo=app["url"],
                                list=self,
                                public_commit=app["git"]["revision"])
                db.session.add(known_app)
            else:
                print("Updating already known app {}".format(name))

            maintainers_info = app["manifest"].get("maintainer", app["manifest"].get("developer", None))
            if maintainers_info is None:
                known_app.maintainers = [ ]
            if isinstance(maintainers_info, dict):
                if maintainers_info["name"] == "-" or maintainers_info["name"] == "":
                    known_app.maintainers = [ ]
                else:
                    known_app.maintainers = re.split(", | et ", maintainers_info["name"])
            if isinstance(maintainers_info, list):
                known_app.maintainers = [ maintainer["name"] for maintainer in maintainers_info ]

            known_app.maintained = app.get("maintained", True)
            known_app.ci_enabled = app["state"] == self.state_for_ci
            known_app.public_level = app.get("level", None)

            if "github" in known_app.repo:
                issues_and_prs = g.issues(known_app)

                known_app.public_commit = app["git"]["revision"]
                known_app.master_commit = g.commit(known_app, "master")
                known_app.testing_diff = g.diff(known_app, "master", "testing")["ahead_by"]
                known_app.opened_issues = issues_and_prs["nb_issues"]
                known_app.opened_prs = issues_and_prs["nb_prs"]

                known_app.public_vs_master_time_diff = \
                   (g.commit_date(known_app, known_app.master_commit) -
                    g.commit_date(known_app, known_app.public_commit)).days
            else:
                known_app.public_commit = "???"
                known_app.master_commit = "???"
                known_app.testing_diff = -1
                known_app.opened_issues = 0
                known_app.opened_prs = 0
                known_app.public_vs_master_time_diff = 0

        try:
           db.session.commit()
        except Exception as e:
           print(e)


class App(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    repo = db.Column(db.String(128), unique=True, nullable=False)
    maintainers = db.Column(db.PickleType)
    maintained = db.Column(db.Boolean, nullable=False)
    ci_enabled = db.Column(db.Boolean, nullable=False)
    public_level = db.Column(db.Integer, default=-1, nullable=True)

    list = db.relationship(AppList, backref='apps', lazy=True, uselist=False)
    list_id = db.Column(db.ForeignKey(AppList.id))

    # 'Status info' stuff
    public_commit = db.Column(db.String(64), nullable=False)
    master_commit = db.Column(db.String(64), nullable=False)
    testing_diff = db.Column(db.Integer, default=-1)
    opened_issues = db.Column(db.Integer, default=-1)
    opened_prs = db.Column(db.Integer, default=-1)
    public_vs_master_time_diff = db.Column(db.Integer, default=9999)

    def __repr__(self):
        return '<App %r>' % self.name

    def init():
        pass

    def most_recent_tests_per_branch(self):

        from appci import AppCIBranch, AppCIResult, AppCI
        branches = AppCIBranch.query.all()
        for branch in branches:
            most_recent_test = AppCIResult.query \
                                          .filter_by(branch = branch) \
                                          .filter_by(app = self) \
                                          .order_by('date desc') \
                                          .first()
            if most_recent_test:
                yield most_recent_test
            else:
                yield AppCIResult(app = self,
                                  branch = branch,
                                  level = None,
                                  date = datetime.datetime.fromtimestamp(0),
                                  results = [ None for t in AppCI.tests ])

class Github():

    def __init__(self):

        from ..settings import GITHUB_USER, GITHUB_TOKEN

        self.user = GITHUB_USER
        self.token = GITHUB_TOKEN

    def request(self, uri, autoretry=True):

        r = requests.get('https://api.github.com/{}'.format(uri), auth=(self.user, self.token)).json()
        if "message" in r and r["message"] == "Not Found" and autoretry:
            time.sleep(30)
            r = requests.get('https://api.github.com/{}'.format(uri), auth=(self.user, self.token)).json()
            if "message" in r and r["message"] == "Not Found":
                print('https://api.github.com/{}'.format(uri))
                return {}
        return r

    def diff(self, app, ref, commit):

        repo = app.repo.replace("https://github.com/", "")
        j = self.request('repos/{}/compare/{}...{}'.format(repo, ref, commit), autoretry=False)

        return { "ahead_by": j.get("ahead_by", -1),
                 "behind_by": j.get("behind_by", -1) }

    def issues(self, app):

        repo = app.repo.replace("https://github.com/", "")
        j = self.request('repos/{}/issues'.format(repo))

        nb_issues = len([ i for i in j if not "pull_request" in i.keys() ])
        nb_prs = len([ i for i in j if "pull_request" in i.keys() ])

        return { "nb_issues": nb_issues,
                 "nb_prs": nb_prs }

    def commit(self, app, ref):

        repo = app.repo.replace("https://github.com/", "")
        j = self.request('repos/{}/git/refs/heads/{}'.format(repo, ref))
        if not "object" in j:
            print('Failed to fetch repos/{}/git/refs/heads/{}'.format(repo, ref))
            return "???"
        return j["object"]["sha"]


    def commit_date(self, app, sha):

        repo = app.repo.replace("https://github.com/", "")
        github_date = self.request('repos/{}/commits/{}'.format(repo, sha))["commit"]["author"]["date"]
        parsed_date = datetime.datetime.strptime(github_date, "%Y-%m-%dT%H:%M:%SZ")
        return parsed_date
