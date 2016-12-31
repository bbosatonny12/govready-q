# Q (by GovReady) - Deployment Scripts for Pivotal Web Services

Q is an information gathering platform for people, tuned to the specific needs of information security and compliance professionals.

This repository contains scripts for deployment to Pivotal Web Services using Cloud Foundry tools.

# Configuration

The Env Variables tab in PWS must be set with some application-specific data in the `ENVIRONMENT_JSON` field. We pass things in via JSON, which if you paste it into the field should lose its newlines to make a really long string (and that's good).

You can copy and modify from this, but _delete the comments_ before you paste it into the environment variable field because comments are not vaid JSON:

	{
	  "debug": true, # Controls the Django DEBUG setting. Should be false in production.
	  "host": "q.govready.com", # domain of main landing site
	  "organization-parent-domain": "govready.com", # parent domain of organization subdomains
	  "admins": [ # List of people who get Django error emails.
	    ["name", "...@govready.com"]
	  ],
	  "secret-key": "....", # make a fresh string for new environments, see Django documentation
	  "email": {
	    "host": "smtp.mailgun.org",
	    "port": "587",
	    "user": "postmaster@mg.govready.com",
	    "pw": "...." # copy from Mailgun
	  },
	  "mailgun_api_key": "key-...", # copy from Mailgun (this is for incoming email)
	  "govready_cms_api_auth": ["...username...", "...password..."]
	}

You'll also need to configure Mailgun to send incoming replies to notification emails to an HTTP hook by giving Mailgun a URL on our domain hosted at PWS.

# Performing a Deployment

To deploy to Pivotal Web Services, run:

	./deploy.sh

This will deploy to the `GovReady` organization `dev` space as the app `govready-q`.

The deploy process installs and runs the Cloud Foundry command-line client, it fetches remote vendor resources (which must be fetched locally prior to upload to PWS), and then it activates a zero-downtime deployment which adds a second instance with new source code, causing load-balancing across old and new code, and then removes the old PWS app running the last deployment.


# Notes

To tinker around with Python interactively on a running PWS container:

	cf ssh govready-q

	# fix somehow incorrect environment
	HOME=~/app/ . ~/app/.profile.d/python.sh 

	python -V


# Credits / License

This repository is licensed under the [GNU GPL v3](LICENSE.md).
