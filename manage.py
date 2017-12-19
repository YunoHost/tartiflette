#!/usr/bin/env python3

from flask_script import Manager, Shell, Command
from app import db, create_app

app = create_app()

def main():
    manager = Manager(app)
    manager.add_command('shell', Shell(make_context=lambda:{"app":app, "db":db}))
    manager.add_command('nuke', Nuke(db))
    manager.add_command('init', Init(db))
    manager.add_command('update', Update(db))
    manager.run()

class Update(Command):

    def __init__(self, db):
        self.db = db

    def run(self):

        from app.models import AppCI
        AppCI.update()


class Nuke(Command):
    """Nuke the database (except the platform table)"""

    def __init__(self, db):
        self.db = db

    def run(self):

        import app.models
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

        stuff_in_module = [ app.models.__dict__.get(s) for s in dir(app.models) ]
        models = [ m for m in stuff_in_module if isinstance(m, type(db.Model)) ]

        for model in models:
            objs = model.init()
            if objs is not None:
                print("> Feeding model %s with init data" % str(model.__name__))
                for obj in model.init():
                    db.session.add(obj)
        db.session.commit()

if __name__ == '__main__':
    main()
