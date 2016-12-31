#!/bin/bash
set -euf -o pipefail # abort script on error

PWS_ORGANIZATION=GovReady
PWS_SPACE=dev
PWS_APPNAME=govready-q
SRC_REPO=git@github.com:GovReady/govready-q.git
SRC_TAG=no_pivotal # branch or tag name in Q repository to deploy

PIP=pip3

# FETCH SOURCES

# Fetch GovReady Q source files.
if [ ! -d src ]; then
	# Make a shallow clone of the source repository.
	git clone \
		-b $SRC_TAG --depth 1 \
		$SRC_REPO src \
		< /dev/null
else
	# Update the repository. 
	(cd src && git fetch $SRC_REPO $SRC_TAG && git checkout FETCH_HEAD)
fi

# CONFIGURE CF CLI

# Install CloudFoundry CLI if it is not already installed.
if [ ! -f /usr/bin/cf ]; then
	curl -L -o /tmp/cf-cli_amd64.deb 'https://cli.run.pivotal.io/stable?release=debian64&source=github'
	sudo dpkg -i /tmp/cf-cli_amd64.deb
	cf -v
fi

# Install blue-green-deploy plugin, if it's not already installed.
if [ ! -f ~/.cf/plugins/blue-green-deploy.linux64 ]; then
	cf install-plugin -f blue-green-deploy -r CF-Community
fi

# Authenticate, if PWS_USER and PWS_PASS are given.
# Since `set -u` requires variables to be defined, we use ${PWS_USER-}
# (i.e. default to empty string) to bypass the check that PWS_USER is
# defined.
if [ ! -z "${PWS_USER-}" ]; then
	cf api https://api.run.pivotal.io
	cf auth $PWS_USER $PWS_PASS
fi

# Set target organization and space.
cf target -o $PWS_ORGANIZATION -s $PWS_SPACE

# PYTHON DEPENDENCIES

# The Python buildpack takes care of installing dependencies for
# us if we create a requirements.txt file here, but Pivotal Web
# Services does not permit network access during this stage of
# deployment. So, per the documentation, we must 'vendorize'
# the dependencies by fetching the packages *locally*. They will
# get uploaded to the application container, which will then
# build & install each.

# Weridly, psycopg2 can't even be downloaded without some
# local system dependencies being available, even though we
# aren't building the packages locally.
if [[ ! -f /usr/bin/pg_config || ! -f /usr/bin/pg_config ]]; then
	sudo apt-get install libpq-dev postgresql-common
fi

# The Python buildpack assumps a requirements.txt file here, so
# create it from the main application dependencies and the Cloud
# Foundry-specific dependencies stored here.
cat src/requirements.txt cf_requirements.txt > requirements.txt

# Pull down all remote dependencies, since that has to happen
# locally before things move off into Pivotal Web Services.
$PIP download --dest vendor --exists-action i \
	-r requirements.txt

# OTHER STATIC ASSETS

# Fetch external static assets served by the website.
(cd src && deployment/fetch-vendor-resources.sh)

# PUSH

# For testing one might just use "cf push" to create or sync
# the existing app. But that method of deployment is not
# graceful. So we don't do this except to create the app
# the first time:
# cf push $PWS_APPNAME -f manifest-template.yaml

# Deploy the update with no downtime by creating a new app,
# updating routes, and then destroying the old app. In order
# to preserve the app's environment variables, we have to
# pull down the current manifest state and store it in
# manifest.yaml so that blue-green-deploy sees it. This has
# the extremely unfortunate side effect of storing any
# secrets in our environment on the local filesystem.
cf create-app-manifest $PWS_APPNAME -p manifest.yaml
cf blue-green-deploy $PWS_APPNAME
rm -f manifest.yaml

# Deauthenticate, if we logged in.
if [ ! -z "${PWS_USER-}" ]; then
	cf logout
fi

