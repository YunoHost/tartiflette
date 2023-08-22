Tartiflette
===========

A dashboard for YunoHost core & app development/packaging

Install
-------

- Clone this repo
- Setup the venv :

```
virtualenv -p python3 venv
source venv/bin/activate
```

- Install the dependencies: 

```
pip install -r requirements.txt
```

- (optional) Configure `GITHUB_USER` and `GITHUB_TOKEN` in `/app/settings.py`. This is currently only required to:
	- override Github's unregistered user API limitation during app catalog update which prevents from updating more than about 10 entries) via `appcatalog.py`
	- perform some maintenance watch tasks via `maintenancePing.py`

- Init the database :

```
./manage.py nuke
./manage.py init
```

- Fetch/update the DB 

```
./manage.py update
```

Note: script files located at `app/scripts/` are meant to be executed via `cron`. Therefore for local development purpose they can be triggered manually.
