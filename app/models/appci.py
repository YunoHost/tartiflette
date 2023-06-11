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
                          arch="amd64",
                          branch="stable",
                          display_name='Stable (x86)',
                          url='https://ci-apps.yunohost.org/ci/api/results',
                          url_per_app='https://ci-apps.yunohost.org/ci/apps/{}/latestjob')

        yield AppCIBranch(name='unstable',
                          arch="amd64",
                          branch="unstable",
                          display_name='Unstable (x86)',
                          url='https://ci-apps-unstable.yunohost.org/ci/logs/list_level_unstable_amd64.json',
                          url_per_app='https://ci-apps-unstable.yunohost.org/ci/apps/{}/latestjob')

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
                yield AppCIResult({"app": app.name,
                                   "architecture": self.arch,
                                   "yunohost_branch": self.branch,
                                   "commit": "",
                                   "level": None,
                                   "timestamp": 0,
                                   "tests": {}})


test_categories = []
def test_category(category_name):
    def decorator(func):
        test_categories.append((func.__name__, category_name, func))
        return func
    return decorator

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

    def __init__(self, infos):

        self.app = App.query.filter_by(name=infos["app"]).first()
        self.branch = AppCIBranch.query.filter_by(arch=infos["architecture"], branch=infos["yunohost_branch"]).first()
        self.level = infos["level"]
        self.commit = infos["commit"]
        self.date = datetime.datetime.fromtimestamp(infos["timestamp"])
        self.results = { category: result for category, result in list(self.analyze_test_categories(infos["tests"])) }

    def analyze_test_categories(self, raw_results):

        for category_id, category_display, is_in_category in test_categories:

            relevant_tests = [test for test in raw_results if is_in_category(test)]

            if not relevant_tests:
                yield (category_id, None)
            else:
                yield (category_id, all(test["main_result"] == "success" for test in relevant_tests))

    @test_category("Linter")
    def package_linter(test):
        return test["test_type"] == "PACKAGE_LINTER"

    @test_category("Install on domain's root")
    def install_root(test):
        return test["test_type"] == "TEST_INSTALL" and test["test_arg"] == "root"

    @test_category("Install on domain subpath")
    def install_subpath(test):
        return test["test_type"] == "TEST_INSTALL" and test["test_arg"] == "subdir"

    @test_category("Install with no url")
    def install_nourl(test):
        return test["test_type"] == "TEST_INSTALL" and test["test_arg"] == "nourl"

    @test_category("Install in private mode")
    def install_private(test):
        return test["test_type"] == "TEST_INSTALL" and test["test_arg"] == "private"

    @test_category("Install multi-instance")
    def install_multi(test):
        return test["test_type"] == "TEST_INSTALL" and test["test_arg"] == "multi"

    @test_category("Upgrade (same version)")
    def upgrade_same_version(test):
        return test["test_type"] == "TEST_UPGRADE" and test["test_arg"] == ""

    @test_category("Upgrade (older versions)")
    def upgrade_older_versions(test):
        return test["test_type"] == "TEST_UPGRADE" and test["test_arg"] != ""

    @test_category("Backup / restore")
    def backup_restore(test):
        return test["test_type"] == "TEST_BACKUP_RESTORE"

    @test_category("Change url")
    def change_url(test):
        return test["test_type"] == "TEST_CHANGE_URL"

    def init():
        pass

    def score(self):
        s_dict = { True: +1, False: -1, None: 0 }
        return sum([ s_dict[result] for result in self.results.values() ])

    @property
    def outdated(self):
        return (datetime.datetime.now() - self.date).days > 30

    @property
    def needs_attention(self):
        return self.outdated or self.level is None or self.app.public_level == "?" or (int(self.app.public_level) > self.level)


class AppCI():

    def update():

        cibranches = AppCIBranch.query.all()

        # Scrap jenkins
        for cibranch in cibranches:
            print("> Fetching current CI results for C.I. branch {}".format(cibranch.name))
            try:
                results = requests.get(cibranch.url).json()
            except:
                print("Failed to fetch %s" % cibranch.url)
                continue

            for app, test_summary in results.items():

                if (test_summary["architecture"], test_summary["yunohost_branch"]) != (cibranch.arch, cibranch.branch):
                    continue

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
                    results = AppCIResult(test_summary)
                    db.session.add(results)

        db.session.commit()
