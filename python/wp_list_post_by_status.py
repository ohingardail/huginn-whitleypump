#! /usr/bin/python
# Script to list Wordpress post via XML RPC
# Designed for use in Huginn (https://github.com/cantino/huginn) 'Shell Command Agent'
# Example agent config :
#{
#  "path": "/home/huginn/scripts/",
#  "command": "/home/huginn/scripts/wp_list_post_by_status.py --url='{% credential wp_xmlrpc %}' --user='{% credential wp_user %}' --password='{% credential wp_password %}' --status='pending'",
#  "suppress_on_failure": "true",
#  "suppress_on_empty_output": "true",
#  "expected_update_period_in_days": "7"
#}

import getopt, sys
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, users
import pprint

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:s:", ["url=", "user=", "password=", "status="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

url = ''
user = None
password = None
status = 'pending'

for o, a in opts:
	if o in ("-x", "--url"):
		url = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a
	elif o in ("-s", "--status"):
		status = a

# get connection to website
try:
	# wordpress = Client('https://whitleypump.wordpress.com/xmlrpc.php', 'whitleypump.uk@gmail.com', 'WhitleyStreet,Reading,RG20EQ')
	# wordpress = Client('https://milmanroad.wordpress.com/xmlrpc.php', 'whitleypump.uk@gmail.com', 'WhitleyStreet,Reading,RG20EQ')
	wordpress = Client(url, user, password)
except:
	print(err)
	sys.exit(1)

# get list of posts
subject_posts = wordpress.call(posts.GetPosts({'post_status': status, 'orderby': 'date', 'order': 'ASC', 'number': 100}))
post_count = len(subject_posts)

if post_count > 0:
	n = 0
	JSON_string = '['
	for subject_post in subject_posts:

		#debug
		#pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)
		#pp.pprint(vars(subject_post))

		# subject_user = wordpress.call(users.GetUser(subject_post.user))
		JSON_string = JSON_string + ' {'
		JSON_string = JSON_string + ' "title":"' + subject_post.title.encode('utf-8') + '",'
		JSON_string = JSON_string + ' "author":"' + subject_post.user + '",'
		# JSON_string = JSON_string + ' "author":"' + subject_user.display_name + '"'
		JSON_string = JSON_string + ' "link":"' + subject_post.link + '",'		
		JSON_string = JSON_string + ' "date":"' + datetime.strftime(subject_post.date, '%d-%b-%Y %H:%M') + '"'

		n = n + 1
		if n < post_count:
			JSON_string = JSON_string + ' },'
		else:
			JSON_string = JSON_string + ' }'

	JSON_string = JSON_string + ' ]'

	print (JSON_string)

