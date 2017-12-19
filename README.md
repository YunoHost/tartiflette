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

- Install the dependencies : 

```
pip install -r requirements.txt
```

- Configure `GITHUB_USER` and `GITHUB_TOKEN` in settings.py

- Init the database :

```
./manage.py nuke
./manage.py init
```

- Fetch/update the DB 

```
./manage.py update
```
