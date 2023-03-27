import re
import time
import json
import requests
import datetime

from .. import db


class AppCatalog():

    def update():

        g = Github()

        raw_apps = json.loads(requests.get("https://app.yunohost.org/default/v3/apps.json").text)
        raw_apps = raw_apps["apps"]

        for name in sorted(raw_apps.keys()):

            app = raw_apps[name]

            app['url'] = app["git"]["url"].strip('/')

            # Try to find an app for this name
            known_app = App.query.filter_by(name=name).first()

            # If this app is not already registered...
            if not known_app:
                print("Adding new app {}".format(name))
                known_app = App(name=name,
                                repo=app["url"],
                                public_commit=app["git"]["revision"])
                db.session.add(known_app)
            else:
                known_app.repo = app["url"]
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

            known_app.maintained = 'package-not-maintained' not in app.get('antifeatures', []),
            known_app.state = app["state"]
            known_app.public_level = app.get("level", None)

            if "github" in known_app.repo:

                known_app.public_commit = app["git"]["revision"]
                known_app.master_commit = g.commit(known_app, "master")
                known_app.public_commit_date = g.commit_date(known_app, known_app.public_commit)
                known_app.master_commit_date = g.commit_date(known_app, known_app.master_commit)
                known_app.testing_pr = g.testing_pr(known_app)

                issues_and_prs = g.issues(known_app)
                known_app.opened_issues = issues_and_prs["nb_issues"]
                known_app.opened_prs = issues_and_prs["nb_prs"]

            else:
                known_app.public_commit = "???"
                known_app.master_commit = "???"
                known_app.testing_pr = None
                known_app.opened_issues = 0
                known_app.opened_prs = 0

            try:
                db.session.commit()
            except Exception as e:
                print(e)
                db.session.rollback()


class App(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    repo = db.Column(db.String(128), unique=True, nullable=False)
    maintainers = db.Column(db.PickleType)
    maintained = db.Column(db.Boolean, nullable=False)
    state = db.Column(db.String(64), nullable=False)
    public_level = db.Column(db.Integer, default=-1, nullable=True)

    # 'Status info' stuff
    public_commit = db.Column(db.String(64), nullable=False)
    master_commit = db.Column(db.String(64), nullable=False)
    public_commit_date = db.Column(db.DateTime, nullable=True)
    master_commit_date = db.Column(db.DateTime, nullable=True)
    testing_pr = db.Column(db.PickleType, default=None)
    opened_issues = db.Column(db.Integer, default=-1)
    opened_prs = db.Column(db.Integer, default=-1)

    long_term_good_quality = db.Column(db.Boolean)
    long_term_broken = db.Column(db.Boolean)

    def __repr__(self):
        return '<App %r>' % self.name

    def init():
        pass

    @property
    def public_vs_master_time_diff(self):
        return (self.public_commit_date - self.master_commit_date).days

    def most_recent_tests_per_branch(self):

        from app.models.appci import AppCIBranch, AppCIResult, AppCI, test_categories
        branches = AppCIBranch.query.all()
        for branch in branches:
            most_recent_test = AppCIResult.query \
                                          .filter_by(branch = branch) \
                                          .filter_by(app = self) \
                                          .order_by(AppCIResult.date.desc()) \
                                          .first()
            if most_recent_test:
                yield most_recent_test
            else:
                yield AppCIResult({"app": self.name,
                                   "architecture": branch.arch,
                                   "yunohost_branch": branch.branch,
                                   "commit": "",
                                   "level": None,
                                   "timestamp": 0,
                                   "tests": {}})

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

    def issues(self, app):

        repo = app.repo.replace("https://github.com/", "")
        j = self.request('repos/{}/issues'.format(repo))

        nb_issues = len([ i for i in j if not "pull_request" in i.keys() ])
        nb_prs = len([ i for i in j if "pull_request" in i.keys() ])

        return { "nb_issues": nb_issues,
                 "nb_prs": nb_prs }

    def testing_pr(self, app):

        repo = app.repo.replace("https://github.com/", "")
        owner = repo.split("/")[0]
        j = self.request('repos/{}/pulls?head={}:testing&base=master'.format(repo,owner))

        if len(j) == 0:
            return None
        else:
            j = j[0]

        return { "number": j["number"],
                 "created_at": datetime.datetime.strptime(j["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                 "updated_at": datetime.datetime.strptime(j["updated_at"], "%Y-%m-%dT%H:%M:%SZ"),
               }


    def commit(self, app, ref):

        repo = app.repo.replace("https://github.com/", "")
        j = self.request('repos/{}/git/refs/heads/{}'.format(repo, ref))
        if not "object" in j:
            print('Failed to fetch repos/{}/git/refs/heads/{}'.format(repo, ref))
            print(j)
            return "???"
        return j["object"]["sha"]


    def commit_date(self, app, sha):

        repo = app.repo.replace("https://github.com/", "")
        try:
           github_date = self.request('repos/{}/commits/{}'.format(repo, sha))["commit"]["author"]["date"]
        except:
           print("Error parsing date...")
           github_date = "1970-01-01T00:00:00Z"
        parsed_date = datetime.datetime.strptime(github_date, "%Y-%m-%dT%H:%M:%SZ")
        return parsed_date
