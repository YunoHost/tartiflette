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

- (optional) For a full local deployment, configure `GITHUB_USER` and `GITHUB_TOKEN` in `/app/settings.py`. This is currently only required to:
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

- Scripts files located at `app/scripts/` are meant to be executed via `cron`. Therefore for local development purpose they can be triggered manually. For instance, to be able to display catalog news and history, run:

```
python app/scripts/appListsHistory/script.py
```
	- That will output a few json files at the repo root (count-history.json, news.json and news_rss.json ) that you will have to move manually to the directory `app/scripts/appListsHistory/`.

- To browse the webapp locally, run from the repo root:

```
flask run
``` 
	- And open the URL that gets displayed in the terminal (e.g. http://127.0.0.1:5000/ ). 
