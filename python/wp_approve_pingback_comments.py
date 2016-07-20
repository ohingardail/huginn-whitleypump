#! /usr/bin/python
# Script to automatically approve pingback comments using Wordpress XML RPC
# Designed for use in Huginn (https://github.com/cantino/huginn) 'Shell Command Agent'
# Example agent config :
#{
#  "path": "/home/huginn/scripts/",
#  "command": "/home/huginn/scripts/wp_approve_pingback_comments.py --url='{% credential wp_xmlrpc %}' --user='{% credential wp_user %}' --password='{% credential wp_password %}'",
#  "suppress_on_failure": "false",
#  "suppress_on_empty_output": "true",
#  "expected_update_period_in_days": "7"
#}

import getopt, sys, pprint
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import comments

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:", ["url=", "user=", "password="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

# hard coded defaults
url = ''
user = ''
password = ''
commentlist = ''

# get commandline options
for o, a in opts:
	if o in ("-x", "--url"):
		url = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a

# get connection to website
try:
	wordpress = Client(url, user, password)
except:
	print('Unable to connect to "' + url + '" with user "' + user + '"' )
	sys.exit(1)

# get list of comments pending approval
subject_comments = wordpress.call(comments.GetComments({'status':'hold', 'number': 100}))
count = len(subject_comments)

if count > 0:
	for subject_comment in subject_comments:

		# check if comment appears to be an auto-pingback
		if (subject_comment.author_email is None or len(subject_comment.author_email) == 0) and len(subject_comment.author_url) > 0 and subject_comment.author_url.find(url.split('/')[2]) and len(subject_comment.link) > 0 and subject_comment.link.find(url.split('/')[2]):

			# dump out post object
			#pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)
			#pp.pprint(vars(subject_comment))

			# approve post
			subject_comment.status = 'approve'
			wordpress.call(comments.EditComment(subject_comment.id, subject_comment))

			if commentlist is None or len(commentlist) == 0:
				commentlist = subject_comment.id
			else:
				commentlist = commentlist + ',' + subject_comment.id
	print commentlist
