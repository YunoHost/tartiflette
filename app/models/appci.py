import json
import requests
import datetime

from .. import db
from app.models.appcatalog import App

class AppCIBranch(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    arch = db.Column(db.String(64), nullable=False)
    branch = db.Column(db.String(64), nullable=False)
    display_name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(128), nullable=False)
    url_per_app = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return '<AppCIBranch %r>' % self.name

    def init():
        yield AppCIBranch(name='stable',
                          arch="x86",
                          branch="stable",
                          display_name='Stable (x86)',
                          url='https://ci-apps.yunohost.org/ci/logs/list_level_stable.json',
                          url_per_app='https://ci-apps.yunohost.org/ci/apps/{}/')

        yield AppCIBranch(name='arm',
                          arch="arm",
                          branch="stable",
                          display_name='Stable (ARM)',
                          url='https://ci-apps-arm.yunohost.org/ci/logs/list_level_stable.json',
                          url_per_app='https://ci-apps-arm.yunohost.org/ci/apps/{}/')

        yield AppCIBranch(name='testing',
                          arch="x86",
                          branch="testing",
                          display_name='Testing (x86)',
                          url='https://ci-apps-unstable.yunohost.org/ci/logs/list_level_testing.json',
                          url_per_app='https://ci-apps-unstable.yunohost.org/ci/apps/{}/')

        yield AppCIBranch(name='unstable',
                          arch="x86",
                          branch="unstable",
                          display_name='Unstable (x86)',
                          url='https://ci-apps-unstable.yunohost.org/ci/logs/list_level_unstable.json',
                          url_per_app='https://ci-apps-unstable.yunohost.org/ci/apps/{}/')

    def last_build_url(self, app):
        return self.url_per_app.format(app.name)

    def most_recent_tests_per_app(self):

        apps = App.query.filter_by(state="working").all()
        most_recent_tests = AppCIResult.query \
                                       .filter_by(branch = self) \
                                       .order_by(AppCIResult.date.desc()) \
                                       .all()

        for app in apps:
            most_recent_test = [ t for t in most_recent_tests if t.app == app ]
            if most_recent_test:
                yield most_recent_test[0]
            else:
                yield AppCIResult(app = app,
                                  branch = self,
                                  level = None,
                                  date = datetime.datetime.fromtimestamp(0),
                                  results = { t:None for t in AppCI.tests })


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
        return '<AppCIResult %s>' % self.date

    def init():
        pass

    def score(self):
        s_dict = { True: +1, False: -1, None: 0 }
        return sum([ s_dict[result] for result in self.results.values() ])

    @property
    def outdated(self):
        return (datetime.datetime.now() - self.date).days > 30


class AppCI():

    tests = [ "Package linter",
              "Installation",
              "Deleting",
              "Installation in a sub path",
              "Deleting from a sub path",
              "Installation on the root",
              "Deleting from root",
              "Upgrade",
              "Installation in private mode",
              "Installation in public mode",
              "Multi-instance installations",
              "Malformed path",
              "Port already used",
              "Backup",
              "Restore",
              "Change URL" ]

    def update():

        cibranches = AppCIBranch.query.all()

        # Scrap jenkins
        for cibranch in cibranches:
            print("> Fetching current CI results for C.I. branch {}".format(cibranch.name))
            try:
                result_json = requests.get(cibranch.url).text
            except:
                print("Failed to fetch %s" % cibranch.url)
                continue
            cleaned_json = [ line for line in result_json.split("\n") if "test_name" in line ]
            cleaned_json = [ line.replace('"level": ?,', '"level": null,') for line in cleaned_json ]
            cleaned_json = "[" + ''.join(cleaned_json)[:-1] + "]"
            cleaned_json = cleaned_json.replace("Binary", '"?"')
            j = json.loads(cleaned_json)
            for test_summary in j:
                if test_summary["app"] is None:
                     print("No app to parse in test_summary ? : %s" % test_summary)
                     continue

                if (test_summary["arch"], test_summary["branch"]) != (cibranch.arch, cibranch.branch):
                    continue

                test_results = { }
                for test, result in zip(AppCI.tests, test_summary["detailled_success"]):
                    test_results[test] = bool(int(result)) if result in [ "1", "0" ] else None

                app = App.query.filter_by(name=test_summary["app"]).first()
                if app is None:
                    print("Couldnt found corresponding app object for %s, skipping" % test_summary["app"])
                    continue
                date = datetime.datetime.fromtimestamp(test_summary["timestamp"])

                existing_test = AppCIResult.query \
                               .filter_by(branch = cibranch) \
                               .filter_by(date = date) \
                               .first()

                if existing_test and existing_test.app is None:
                    print("Uh erasing old weird buggy record")
                    db.session.delete(existing_test)
                    existing_test = None

                if not existing_test:
                        print("New record for app %s" % str(app))
                        results = AppCIResult(app = app,
                                              branch = cibranch,
                                              level = test_summary["level"],
                                              date = date,
                                              results = test_results)
                        db.session.add(results)

        db.session.commit()
