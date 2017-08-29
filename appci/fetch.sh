#!/bin/bash

python fetchlist.py | sort > list_apps 

while read APP;
do
	APPNAME=$(echo $APP | awk '{print $1}')
	echo $APPNAME
	wget -q -O data/$APPNAME "https://ci-apps.yunohost.org/jenkins/job/$APP/lastBuild/consoleText" --prefer-family=IPv4

	TESTS_RESULTS=""
	while read TESTNAME
	do
		RESULTS=$(grep "^$TESTNAME:" data/$APPNAME)
		if echo $RESULTS | grep -q "FAIL"
		then
			TESTS_RESULTS="${TESTS_RESULTS}0"
		elif echo $RESULTS | grep -q "SUCCESS"
		then
			TESTS_RESULTS="${TESTS_RESULTS}1"
		else
			TESTS_RESULTS="${TESTS_RESULTS}X"
		fi
	done < list_tests

	LEVELS=$(grep -A10 'Level of this application' data/$APPNAME \
		| tail -n 11 \
		| sed -e 's@N/A@X@g' -e 's/	   Level //g' -e 's/Level of this application//g' \
		| awk '{print $2}' \
		| tr -d '\n')

	echo $TESTS_RESULTS > data/$APPNAME
	echo $LEVELS >> data/$APPNAME

done < list_apps

