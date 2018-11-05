import json
import requests
import datetime

from .. import db
from app.models.applists import App

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

        apps = App.query.filter_by(ci_enabled=True).all()
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
