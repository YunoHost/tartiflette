import json
import requests
import datetime

from .. import db


class Repo(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(64), unique=True, nullable=False)
    team = db.Column(db.String(64), nullable=False)

    def __repr__(self):
        return '<Repo %r>' % self.name

    def init():

        d = {
            "core": ["yunohost",
                     "yunohost-admin",
                     "SSOwat",
                     "moulinette",
                     "Vagrantfile",
                     "ynh-dev"],

            "doc": ["doc",
                    "Simone",
                    "project-organization"],

            "apps": ["apps",
                     "CI_package_check",
                     "example_ynh",
                     "package_linter",
                     "package_check"],

            "infra": ["build.yunohost.org",
                      "dynette",
                      "YunoPorts",
                      "cd_build",
                      "install_script",
                      "trotinette",
                      "bicyclette",
                      "install-app",
                      "tartiflette",
                      "vinaigrette"]
        }

        for team, repos in d.items():
            for repo in repos:
                yield Repo(name=repo, team=team)

    def update(self):

        print("Updating PRs for repo %s ..." % self.name)

        PullRequest.query.filter_by(repo=self).delete()

        issues = requests.get("https://api.github.com/repos/yunohost/%s/issues?per_page=100" % self.name)
        issues = json.loads(issues.text)
        issues = [i for i in issues if "pull_request" in i.keys()]

        for issue in issues:
            print("  > Analyzing %s-%s" % (self.name, issue["number"]))
            db.session.add(PullRequest(self, issue))

        db.session.commit()


class PullRequest(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    id_ = db.Column(db.String(64), unique=True, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    labels = db.Column(db.PickleType)
    url = db.Column(db.String(128), nullable=False)
    milestone = db.Column(db.String(32), nullable=False)
    
    review_priority = db.Column(db.Integer)

    created = db.Column(db.DateTime)
    updated = db.Column(db.DateTime)

    repo = db.relationship(Repo, backref='prs', lazy=True, uselist=False)
    repo_id = db.Column(db.ForeignKey(Repo.id))

    def __init__(self, repo, issue):

        self.repo = repo
        self.title = issue["title"]
        self.labels = [label["name"] for label in issue["labels"]]
        self.milestone = issue["milestone"]["title"] if issue["milestone"] else ""

        self.id_ = "%s-%s" % (repo.name, issue["number"])

        self.created = datetime.datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        self.updated = datetime.datetime.strptime(issue["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
        self.url = issue["pull_request"]["html_url"]

        for size in ["small", "medium", "big"]:
            if "%s decision" % size in self.labels:
                self.labels.remove("%s decision" % size)
                self.labels.insert(0, size)

        now = datetime.datetime.now()
        if (now - self.created).days > 60 and (now - self.updated).days > 30:
            self.labels.append("dying")

        self.review_priority = self.get_review_priority()

    def get_review_priority(self):
        if "important" in self.labels:
            base_priority = 100
        elif "opinion needed" in self.labels:
            base_priority = 50
        elif "postponed" in self.labels or "inactive" in self.labels:
            base_priority = -100
        else:
            base_priority = 0

        if "work needed" in self.labels:
            base_priority += -5

        if "dying" in self.labels and base_priority > -100:
            base_priority += 5

        return base_priority
    
    def init():
        pass

