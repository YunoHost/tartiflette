from datetime import datetime
from flask import render_template, make_response, Blueprint
from .models.pr import PullRequest
from .models.appcatalog import App
from .models.appci import AppCI, AppCIBranch, test_categories
from .models.unlistedapps import UnlistedApp
from .settings import SITE_ROOT
import json
import os

main = Blueprint('main', __name__, url_prefix=SITE_ROOT)

def sort_test_results(results):

    results = list(results)

    for r in results:
        r.level = -1 if r.level is None else r.level

    return sorted(results,
                  key=lambda r: (-r.level, -r.score(), r.app.name))


@main.route('/')
def index():
    return render_template('index.html')

@main.route('/pullrequests')
def pullrequests():

    prs = PullRequest.query.all()

    prs = sorted(prs, key=lambda pr: (pr.review_priority, pr.created), reverse=True)

    active_prs = [ pr for pr in prs if pr.review_priority >= 0]
    count_by_team = { "all": len(active_prs),
                      "core": len([pr for pr in active_prs if pr.repo.team == "core"]),
                      "apps": len([pr for pr in active_prs if pr.repo.team == "apps"]),
                      "infra": len([pr for pr in active_prs if pr.repo.team == "infra"]),
                      "doc": len([pr for pr in active_prs if pr.repo.team == "doc"]) }

    return render_template("pullrequests.html", prs=prs,  count_by_team=count_by_team)

#
# Apps CI
#


@main.route('/appci/branch/<branch>')
def appci_branch(branch):

    branch = AppCIBranch.query.filter_by(name=branch).first_or_404()

    app_results = sort_test_results(branch.most_recent_tests_per_app())

    return render_template("appci_branch.html", test_categories=test_categories,
                                                branch=branch,
                                                app_results=app_results)


@main.route('/appci/app/<app>')
def appci_app(app):

    app = App.query.filter_by(name=app).first_or_404()

    branch_results = list(app.most_recent_tests_per_branch())

    for r in branch_results:
        r.level = -1 if r.level in ["?", None] else int(r.level)

    history_file = "./app/scripts/appListsHistory/per_app/history_%s.json" % app.name
    if os.path.exists(history_file):
        history = json.loads(open(history_file).read())
    else:
        history = []

    return render_template("appci_app.html", test_categories=test_categories,
                                             app=app,
                                             branch_results=branch_results,
                                             history=history)


@main.route('/appci/compare/<ref>...<target>')
def appci_compare(ref, target):

    assert ref != target, "Can't compare the same branches, bruh"

    ref = AppCIBranch.query.filter_by(name=ref).first_or_404()
    target = AppCIBranch.query.filter_by(name=target).first_or_404()

    ref_results = sort_test_results(ref.most_recent_tests_per_app())
    target_results = sort_test_results(target.most_recent_tests_per_app())

    for ref_r in ref_results:
        ref_r.level_compare = next((r.level for r in target_results
                                                if r.app == ref_r.app),
                                    -1)
        if ref_r.level == -1 or ref_r.level_compare == -1:
            ref_r.compare = "unknown"
        elif ref_r.level == ref_r.level_compare:
            ref_r.compare = "same"
        elif ref_r.level > ref_r.level_compare:
            if ref_r.level_compare == 0:
                ref_r.compare = "broken"
            else:
                ref_r.compare = "regression"
        elif ref_r.level < ref_r.level_compare:
            ref_r.compare = "improvement"
        else:
            ref_r.compare = "unknown"

    return render_template("appci_compare.html", ref=ref,
                                                 target=target,
                                                 results=ref_results)

@main.route('/integration/<app>')
@main.route('/integration/<app>.svg')
@main.route('/badge/<type>/<app>')
@main.route('/badge/<type>/<app>.svg')
def badge(app, type="integration"):

    apps = App.query.filter_by(name=app).all()
    app = apps[0] if len(apps) == 1 else None
    level = None

    if app:
        branch_results = list(app.most_recent_tests_per_branch())
        for r in branch_results:
            if r.branch.name == "stable":
                level = r.level
                break

    if type == "integration":
        if app and app.state == "working" and level:
            badge = f"level{level}"
        else:
            badge = "unknown"
    elif type == "state":

        if not app:
            badge = "state-unknown"
        elif app.state == "working":
            if app.public_level is None or app.public_level == "?":
                badge = "state-just-got-added-to-catalog"
            elif app.public_level in [0, -1]:
                badge = "state-broken"
            else:
                badge = "state-working"
        else:
            badge = f"state-{app.state}"
    elif type == "maintained":
        if app and not app.maintained:
            badge = "unmaintained"
        else:
            badge = "empty"
    else:
            badge = "empty"

    svg = open(f"./app/static/badges/{badge}.svg").read()
    response = make_response(svg)
    response.content_type = 'image/svg+xml'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'

    return response

#
# Apps observatory
#

@main.route('/applist_history')
@main.route('/appsobservatory/history')
def appsobservatory_history():
    data = json.loads(open("./app/scripts/appListsHistory/count_history.json").read())
    return render_template('applist_history.html', data=data)


@main.route('/appsobservatory/news')
def appsobservatory_news():
    news_per_date = json.loads(open("./app/scripts/appListsHistory/news.json").read())
    return render_template('applist_news.html', news_per_date=list(reversed(list(news_per_date.items()))))


@main.route('/appsobservatory/unlisted')
def appsobservatory_unlisted():

    apps = sorted(UnlistedApp.query.all(), key=lambda a: a.updated_days_ago)

    return render_template("unlistedapps.html", apps=apps)

@main.route('/app_maintainer_dash')
@main.route('/app_maintainer_dash/<maintainer>')
def app_maintainer_dash(maintainer=None):

    if maintainer:
        maintainer = maintainer.lower().replace(" ", "")

    maintainers = set()
    apps = App.query.all()
    for app in apps:
        for test in app.most_recent_tests_per_branch():
            if test.branch.name == "stable":
                app.ci_level = test.level

        if isinstance(app.public_level, str):
            app.public_level = -1

        if app.maintained and app.state == "working":
            maintainers.update(app.maintainers)

    maintainers = sorted(maintainers, key=lambda m: m.lower())
    apps = sorted(apps, key=lambda app: app.name.lower())

    return render_template("maintainer.html", maintainers=maintainers, apps=apps, maintainer=maintainer)

@main.route('/testings')
def testings():

    apps = App.query.filter(App.testing_pr!=None).all()

    def daysAgo(date):
        return (datetime.now() - date).days

    for app in apps:
        app.testing_pr["created_ago"] = daysAgo(app.testing_pr["created_at"])
        app.testing_pr["updated_ago"] = daysAgo(app.testing_pr["updated_at"])

    apps = sorted(apps, key=lambda app: (-app.testing_pr["created_ago"], -app.testing_pr["updated_ago"], app.name.lower()))

    return render_template("testings.html", apps=apps)
