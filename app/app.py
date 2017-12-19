from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from .models import App, AppCI, AppCIBranch

app = Flask(__name__)

def sort_test_results(results):

    results = list(results)

    for r in results:
        r.level = -1 if r.level is None else r.level

    print(results)

    return sorted(results,
                 key=lambda r: (-r.level, -r.score(), r.app.name))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/appci/branch/<branch>')
def appci_branch(branch):

    branch = AppCIBranch.query.filter_by(name=branch).first_or_404()

    app_results = sort_test_results(branch.most_recent_tests_per_app())

    return render_template("appci_branch.html", tests=AppCI.tests,
                                                branch=branch,
                                                app_results=app_results)

@app.route('/appci/app/<app>')
def appci_app(app):

    app = App.query.filter_by(name=app).first_or_404()

    branch_results = list(app.most_recent_tests_per_branch())

    for r in branch_results:
        r.level = -1 if r.level is None else r.level

    return render_template("appci_app.html", tests=AppCI.tests,
                                             app=app,
                                             branch_results=branch_results)

@app.route('/appci/compare/<ref>...<target>')
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

    return render_template("appci_compare.html", ref=ref,
                                                 target=target,
                                                 results=ref_results)

