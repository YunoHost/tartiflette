#!/bin/bash

for PAGEID in `seq 1 5`
do
	curl "https://api.github.com/search/repositories?q=_ynh&sort=updated&per_page=100&page=$PAGEID" > data/$PAGEID.json
done
