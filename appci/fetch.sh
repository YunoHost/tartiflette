#!/bin/bash

while read APP;
do
	APPNAME=$(echo $APP | awk '{print $1}')
	echo $APPNAME
	wget -q -O data/$APPNAME "https://ci-apps.yunohost.org/jenkins/job/$APP/lastBuild/consoleText" --prefer-family=IPv4

	CHECKS=$(cat data/$APPNAME | grep "Package linter:" -A15 | tail -n 16 | sed -e 's/FAIL/0/g' -e 's/SUCCESS/1/g' -e 's/Not evaluated./X/' | awk '{print $NF}' | tr -d '\n')
	LEVELS=$(cat data/$APPNAME | grep 'Level of this application'  -A10 | tail -n 11 | sed -e 's@N/A@X@g' -e 's/	   Level //g' -e 's/Level of this application//g' | awk '{print $2}' | tr -d '\n')

	echo $CHECKS > data/$APPNAME
	echo $LEVELS >> data/$APPNAME

done < apps

