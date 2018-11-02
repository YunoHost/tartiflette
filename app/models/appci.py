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
                      url="https://raw.githubusercontent.com/YunoHost/apps/master/official.json",
                      state_for_ci='validated')
        yield AppList(name='community',
                      url="https://raw.githubusercontent.com/YunoHost/apps/master/community.json",
                      state_for_ci='working')

    def update(self):

        g = Github()

        raw_apps = json.loads(requests.get(self.url).text).values()
        apps_for_ci = [ app for app in raw_apps
                        if app["state"] == self.state_for_ci ]

        for app in apps_for_ci:

            app['url'] = app["url"].strip('/')
            name = os.path.basename(app["url"]).replace("_ynh", "")

            # Try to find an app for this name
            known_app = App.query.filter_by(name=name).first()

            # If this app is not already registered...
            if not known_app:
                print("Adding new app {}".format(name))
                known_app = App(name=name,
                                repo=app["url"],
                                list=self,
                                public_commit=app["revision"])
                db.session.add(known_app)
            else:
                print("Updating already known app {}".format(name))

            if "github" in known_app.repo:
                issues_and_prs = g.issues(known_app)

                known_app.public_commit = app["revision"]
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

class AppCIBranch(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    arch = db.Column(db.String(64), nullable=False)
    branch = db.Column(db.String(64), nullable=False)
    display_name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(128), nullable=False)
    console_uri = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return '<AppCIBranch %r>' % self.name

    def init():
        yield AppCIBranch(name='stable',
                          arch="x86",
                          branch="stable",
                          display_name='Stable (x86)',
                          url='https://ci-apps.yunohost.org/ci/logs/list_level_stable.json',
                          console_uri='/job/{} ({})/lastBuild/consoleText')

        yield AppCIBranch(name='arm',
                          arch="arm",
                          branch="stable",
                          display_name='Stable (ARM)',
                          url='https://ci-apps-arm.yunohost.org/ci/logs/list_level_stable.json',
                          console_uri='/job/{} ({}) (~ARM~)/lastBuild/consoleText')

    def last_build_url(self, app):
        return self.url + self.console_uri.format(app.name, app.list.name.title())

    def most_recent_tests_per_app(self):

        apps = App.query.all()
        for app in apps:
            most_recent_test = AppCIResult.query \
                                          .filter_by(branch = self) \
                                          .filter_by(app = app) \
                                          .order_by('date desc') \
                                          .first()
            if most_recent_test:
                yield most_recent_test
            else:
                yield AppCIResult(app = app,
                                  branch = self,
                                  level = None,
                                  date = datetime.datetime.fromtimestamp(0),
                                  results = [ None for t in AppCI.tests ])


class AppCIResult(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    app = db.relationship(App, backref='tests', lazy=True, uselist=False)
    branch = db.relationship(AppCIBranch, backref='tests', lazy=True, uselist=False)

    app_id = db.Column(db.ForeignKey(App.id))
    branch_id = db.Column(db.ForeignKey(AppCIBranch.id))

    results = db.Column(db.PickleType)

    date = db.Column(db.DateTime, nullable=True)
    level = db.Column(db.Integer, nullable=True)
    url = db.Column(db.String(128), nullable=True)
    commit = db.Column(db.String(64), nullable=True)

    def __repr__(self):
        return '<AppTestResults %s>' % self.date

    def init():
        pass

    def score(self):
        s_dict = { True: +1, False: -1, None: 0 }
        return sum([ s_dict[result] for result in self.results ])


class AppCI():

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

    def update():

        applists = AppList.query.all()

        # Updating applists...
        for applist in applists:
            applist.update()

        cibranches = AppCIBranch.query.all()

        def symbol_to_bool(s):
            return bool(int(s)) if s in [ "1", "0" ] else None

        # Scrap jenkins
        for cibranch in cibranches:
            print("> Fetching current CI results for C.I. branch {}".format(cibranch.name))
            result_json = requests.get(cibranch.url).text
            cleaned_json = [ line for line in result_json.split("\n") if "test_name" in line ]
            cleaned_json = [ line.replace('"level": ?,', '"level": null,') for line in cleaned_json ]
            cleaned_json = "[" + ''.join(cleaned_json)[:-1] + "]"
            j = json.loads(cleaned_json)
            for test_summary in j:
                if (test_summary["arch"], test_summary["branch"]) != (cibranch.arch, cibranch.branch):
                    continue

                results = AppCIResult(app = App.query.filter_by(name=test_summary["app"]).first(),
                                      branch = cibranch,
                                      level = test_summary["level"],
                                      date = datetime.datetime.fromtimestamp(test_summary["timestamp"]),
                                      results = [ symbol_to_bool(s) for s in test_summary["detailled_success"] ])
                db.session.add(results)

        db.session.commit()


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
