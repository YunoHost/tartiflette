from flask import render_template, make_response, Blueprint
from .models.pr import PullRequest
from .models.appci import App, AppCI, AppCIBranch
from .settings import SITE_ROOT
import json

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

    return render_template("appci_branch.html", tests=AppCI.tests,
                                                branch=branch,
                                                app_results=app_results)


@main.route('/appci/app/<app>')
def appci_app(app):

    app = App.query.filter_by(name=app).first_or_404()

    branch_results = list(app.most_recent_tests_per_branch())

    for r in branch_results:
        r.level = -1 if r.level is None else r.level

    return render_template("appci_app.html", tests=AppCI.tests,
                                             app=app,
                                             branch_results=branch_results)


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
def badge(app):

    app = App.query.filter_by(name=app).first_or_404()
    branch_results = list(app.most_recent_tests_per_branch())
    level = None
    for r in branch_results:
        if r.branch.name == "stable":
            level = r.level
            break

    badge = "level%s.svg" % level if not level is None else "unknown.svg"

    svg = open("./app/static/badges/%s" % badge).read()
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


@main.route('/appsobservatory/rss')
def appsobservatory_rss():
    file_ = open("./app/scripts/appListsHistory/atom.xml").read()
    response = make_response(file_)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response

