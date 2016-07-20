#! /usr/bin/python
# Script to use post a new Wordpress post via XML RPC
# Designed for use in Huginn (https://github.com/cantino/huginn) 'Shell Command Agent'
# Example agent config :
# {
#  "path": "/home/huginn/scripts/",
#  "command": "/home/huginn/scripts/wp_new_post.py --url='{% credential wp_xmlrpc %}' --user='{% credential wp_user %}' --password='{% credential wp_password %}' --title='{{ title }}' --content='{{ body }}' --category='{{ category }}' --status='{{ status | default: default_status }}' --date='{{ delay }}'",
# "suppress_on_failure": "false",
#  "suppress_on_empty_output": "false",
#  "expected_update_period_in_days": 1
#}

import getopt, sys, pprint
from datetime import *
import dateutil.parser
from dateutil.tz import *
#from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, taxonomies

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:s:t:c:g:d:", ["url=", "user=", "password=", "status=", "title=", "content=", "category=", 'date='])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

# hard coded defaults
url = ''
user = None
password = None
status = 'draft'
title = None
content = None
categories = None
post_date = None

# get commandline options
for o, a in opts:
	if o in ("-x", "--url"):
		url = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a
	elif o in ("-s", "--status"):
		status = a
	elif o in ("-t", "--title"):
		title = a
	elif o in ("-c", "--content"):
		content = a
	elif o in ("-g", "--category"):
		categories = a
	elif o in ("-d", "--date"):
		post_date = a

# get connection to website
try:
	wordpress = Client(url, user, password)
except:
	print(err)
	sys.exit(1)

# check basic info has been provided
if title is not None and content is not None:

	# TODO clean up content
	# title plaintext only
	# [more] after first para
	# all pics and links are target=_blank

	# assemble post object (as draft first)
	new_post = WordPressPost()
	new_post.status = 'draft'
	new_post.title = title
	new_post.content = content
	new_post.comment_status = 'open'
	new_post.ping_status = 'open'

	if post_date is not None and len(post_date.strip()) > 0:
		 #new_post.date = dateutil.parser.parse(post_date + " " + datetime.now(tzlocal()).tzname())
		new_post.date = dateutil.parser.parse(post_date)

	# categorise post
	if categories is not None and len(categories.strip()) > 0:
		for category in categories.split(','):
			category_objects = wordpress.call(taxonomies.GetTerms('category', {'search': category, 'orderby': 'count', 'number': 1}))
			if category_objects != None:
				for category_object in category_objects:
					new_post.terms.append(category_object)

	# dump out post object
	#pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)
	#pp.pprint(vars(new_post))

	# Actually post new post object
	new_post.id = wordpress.call(posts.NewPost(new_post))

	# post-fix post (mainly for WP weirdness about posting directly to 'pending' status)
	change = False
	if status == 'pending' and new_post.status != status:
		new_post.post_status = status
		change = True

	if change:
		wordpress.call(posts.EditPost(new_post.id, new_post))
	
	# dump out new post ID
	print new_post.id
