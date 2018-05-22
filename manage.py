#!/usr/bin/env python3

from flask_script import Manager, Shell, Command, Server
from app import db, create_app

app = create_app()


def main():
    manager = Manager(app)
    manager.add_command('shell', Shell(make_context=lambda:{"app":app, "db":db}))
    manager.add_command('nuke', Nuke(db))
    manager.add_command('init', Init(db))
    manager.add_command('update-appci', Update(db, "appci"))
    manager.add_command('update-pr', Update(db, "pr"))
    manager.add_command("runserver", Server())
    manager.run()


class Update(Command):

    def __init__(self, db, what):
        self.db = db
        self.what = what

    def run(self):

        if self.what == "appci":
            from app.models.appci import AppCI
            AppCI.update()
        elif self.what == "pr":
            from app.models.pr import Repo
            for repo in Repo.query.all():
                repo.update()
        else:
            pass


class Nuke(Command):
    """Nuke the database (except the platform table)"""

    def __init__(self, db):
        self.db = db

    def run(self):

        import app.models.appci
        import app.models.pr

        print("> Droping tables...")
        self.db.drop_all()
        print("> Creating tables...")
        self.db.create_all()
        print("> Comitting sessions...")
        self.db.session.commit()


class Init(Command):

    def __init__(self, db):
        self.db = db

    def run(self):
        import app.models

        # Black magic to extract list of models from 'models' folder
        submodules = [ app.models.__dict__.get(m) for m in dir(app.models) if not m.startswith('__') ]
        stuff = []
        for submodule in submodules:
            stuff.extend([submodule.__dict__.get(s) for s in dir(submodule)])
        models = [s for s in stuff if isinstance(s, type(db.Model))]

        for model in models:
            objs = model.init()
            if objs is not None:
                print("> Feeding model %s with init data" % str(model.__name__))
                for obj in model.init():
                    db.session.add(obj)
        db.session.commit()


if __name__ == '__main__':
    main()
