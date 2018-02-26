import os
import json
import requests
import dateutil.parser

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

            issues_and_prs = g.issues(known_app)

            known_app.public_commit = app["revision"]
            known_app.master_commit = g.commit(known_app, "master")
            known_app.testing_diff = g.diff(known_app, "master", "testing")["ahead_by"]
            known_app.opened_issues = issues_and_prs["nb_issues"]
            known_app.opened_prs = issues_and_prs["nb_prs"]

        db.session.commit()



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



class AppCIBranch(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    display_name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(128), nullable=False)
    console_uri = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return '<AppCIBranch %r>' % self.name

    def init():
        yield AppCIBranch(name='stable',
                          display_name='Stable (x86)',
                          url='https://ci-apps.yunohost.org/jenkins',
                          console_uri='/job/{} ({})/lastBuild/consoleText')

        yield AppCIBranch(name='arm',
                          display_name='Stable (ARM)',
                          url='https://ci-apps.yunohost.org/jenkins',
                          console_uri='/job/{} ({}) (~ARM~)/lastBuild/consoleText')

        yield AppCIBranch(name='stretch',
                          display_name='Stretch (x86)',
                          url="http://212.47.243.98:8080",
                          console_uri="/job/{} ({})/lastBuild/consoleText")


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


class AppCIResult(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    app = db.relationship(App, backref='tests', lazy=True, uselist=False)
    branch = db.relationship(AppCIBranch, backref='tests', lazy=True, uselist=False)

    app_id = db.Column(db.ForeignKey(App.id))
    branch_id = db.Column(db.ForeignKey(AppCIBranch.id))

    results = db.Column(db.PickleType)

    date = db.Column(db.DateTime, nullable=True)
    level = db.Column(db.Integer, nullable=True)
    url = db.Column(db.String(128), nullable=False)
    commit = db.Column(db.String(64), nullable=True)

    def __repr__(self):
        return '<AppTestResults %s>' % self.date

    def init():
        pass

    def score(self):
        s_dict = { True: +1, False: -1, None: 0 }
        return sum([ s_dict[result] for result in self.results.values() ])


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

        apps = App.query.all()
        cibranches = AppCIBranch.query.all()

        # Scrap jenkins
        for branch in cibranches:
            for app in apps:
                print("> Fetching {} for C.I. branch {}".format(app.name, branch.name))
                url, raw_ci_output = AppCI.fetch_raw_ci_output(branch, app)
                if raw_ci_output is None:
                    print("  Not found, going next")
                    continue
                print("> Analyzing...")
                results = AppCI.scrap_raw_ci_output(raw_ci_output)
                print("> Saving...")
                results = AppCIResult(app = app,
                                      branch = branch,
                                      url = url,
                                      date = results["date"],
                                      level = results["level"],
                                      results = results["tests"],
                                      commit = results["commit"])
                db.session.add(results)

        db.session.commit()


    def fetch_raw_ci_output(cibranch, app):

        console_url = cibranch.last_build_url(app)
        r = requests.get(console_url)
        return (console_url, r.text.split('\n') if r.status_code == 200 else None)


    def scrap_raw_ci_output(raw_console):

        tests_results = {}

        # Find individual tests results
        for test in AppCI.tests:
            # A test can have been done several times... We grep all lines
            # corresponding to this test
            test_results = [ line for line in raw_console if line.startswith(test+":") ]

            # For each line corresponding to this test, if there's at least one
            # failed, it means this test failed
            if [ line for line in test_results if "FAIL" in line ]:
                tests_results[test] = False
            # Otherwise, if there's at least one success, it means this test
            # succeeded
            elif [ line for line in test_results if "SUCCESS" in line ]:
                tests_results[test] = True
            # Otherwise, this means it has not been evaluated
            else:
                tests_results[test] = None

        # Find level
        level = None
        for line in raw_console:
            if line.startswith('Level of this application:'):
                try:
                    level = int(line.replace('Level of this application:', '').split()[0])
                except:
                    print("Couldn't parse level :s")

        # Find date
        date = None
        for previous_line, line in zip(raw_console, raw_console[1:]):
          if line == "Test finished.":
              # Get date from previous line and parse it into a timestamp
              date = previous_line
              try:
                date = dateutil.parser.parse(date)
              except:
                # Meh
                date = None

        # Find commit
        commit = None
        for line in raw_console:
            if line.startswith('Checking out Revision '):
                commit = line.split()[3]

        return {
            "tests": tests_results,
            "level": level,
            "date": date,
            "commit": commit
        }


class Github():

    def __init__(self):

        from ..settings import GITHUB_USER, GITHUB_TOKEN

        self.user = GITHUB_USER
        self.token = GITHUB_TOKEN

    def request(self, uri):

        r = requests.get('https://api.github.com/{}'.format(uri), auth=(self.user, self.token))
        return r.json()

    def diff(self, app, ref, commit):

        repo = app.repo.replace("https://github.com/", "")
        j = self.request('repos/{}/compare/{}...{}'.format(repo, ref, commit))

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
        return self.request('repos/{}/git/refs/heads/{}'.format(repo, ref))["object"]["sha"]
