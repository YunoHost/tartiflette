Tartiflette
===========

A quick and dirty PR dashboard for yunohost's repos

Install
-------

- Clone this repo
- Download and unzip Eden UI into www : http://scripteden.com/download/eden-ui-bootstrap-3-skin/
- Install dependencies :
```
apt install -y python3-pip
pip3 install ansi2html jinja2
```
- Make your web browser serve www/index.html

Usage
-----

```
./fetch.py
./analyze.py
./publish.py
```

- Edit repos.json if needed
- Don't know the number of API calls someone is allowed to do, so limit the call
to fetch.py :/
- HTML template is pretty dirty so far and should be cleaned

