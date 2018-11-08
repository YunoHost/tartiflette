#!/bin/bash

readonly TOKEN="$(cat token)"
readonly TITLE="Consider adding the app to the community list"
readonly BODY="Hello !\n\nThis is a friendly automatic notice from the Yunohost Apps team : our tool noticed that your app is pretty interesting but is not listed in the [community list](https://github.com/YunoHost/apps/blob/master/community.json) !\n\nPlease consider making a pull request to add it, such that people can easily learn about its existence from [this page](https://yunohost.org/#/apps). If you declare your app as working, you might also benefit from [automatic tests on the app C.I.](https://ci-apps.yunohost.org/).\n\nIt is relevant to add your app to the list even if it's not working or unmaintained since it might still help people who might want to continue packaging the app. Just be sure to correctly flag it as notworking/unmaintained.\n\nCheckout the README to learn [how to add your app to the list](https://github.com/YunoHost/apps#how-to-add-your-app-to-the-community-list) (should take only a few minutes).\n\nDatalove <3,\n\nThe YunoHost team."

function createIssue()
{
    local OWNER=$1
    local REPO=$2
    local DATA='{ "title":"'"$TITLE"'", "body":"'"$BODY"'" }'

    ANSWER=$(curl https://api.github.com/repos/$OWNER/$REPO/issues \
                  -H "Authorization: token $TOKEN" \
                  --data "$DATA" )
    #echo "$ANSWER" >&2

    echo "$ANSWER"
    echo "$ANSWER" \
    | grep "^  \"html_url\":" \
    | awk '{print $2}' \
    | tr '"' ' ' \
    | awk '{print $1}'

}

function main()
{

	local OWNER
	local REPO

	while read -r line
	do
		echo $line
		OWNER=$(echo "$line" | tr '/' ' ' | awk '{print $3}')
		REPO=$(echo "$line" | tr '/' ' ' | awk '{print $4}')
		createIssue $OWNER $REPO
		sleep 0.5
	done < ./appstocall

}

main
