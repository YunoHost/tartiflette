#!/usr/bin/env python3

from flask_script import Manager, Shell, Command, Server
from app import db, create_app

app = create_app()
manager = Manager(app)
def main():
    manager.add_command('shell', Shell(make_context=lambda:{"app":app, "db":db}))
    manager.add_command("runserver", Server())
    manager.run()

@manager.add_command
class Update(Command):
    name = "update"
    capture_all_args = True

    def run(self, args=None):

        valid_what = ["applists", "appci", "pr", "appobservatory"]
        what = args[0] if args else None
        assert what in valid_what, "Please specify what to update among %s" % ', '.join(valid_what)

        if what == "applists":
            from app.models.applists import AppList
            AppList.update()
        elif what == "appci":
            from app.models.appci import AppCI
            AppCI.update()
        elif what == "pr":
            from app.models.pr import Repo
            for repo in Repo.query.all():
                repo.update()
        elif what == "appobservatory":
            from app.models.unlistedapps import UnlistedApp
            UnlistedApp.update()
        else:
            pass


@manager.add_command
class Nuke(Command):
    """Nuke the database (except the platform table)"""
    name = "nuke"

    def run(self):

        import app.models.applists
        import app.models.appci
        import app.models.pr
        import app.models.unlistedapps

        print("> Droping tables...")
        db.drop_all()
        print("> Creating tables...")
        db.create_all()
        print("> Comitting sessions...")
        db.session.commit()


@manager.add_command
class Init(Command):
    name = "init"

    def run(self):
        import app.models

        # Black magic to extract list of models from 'models' folder
        submodules = [ app.models.__dict__.get(m) for m in dir(app.models) if not m.startswith('__') ]
        stuff = []
        for submodule in submodules:
            stuff.extend([submodule.__dict__.get(s) for s in dir(submodule)])
        models = [s for s in stuff if isinstance(s, type(db.Model))]
        models = set(models)

        for model in models:
            objs = model.init()
            if objs is not None:
                print("> Feeding model %s with init data" % str(model.__name__))
                for obj in model.init():
                    db.session.add(obj)
        db.session.commit()


if __name__ == '__main__':
    main()
