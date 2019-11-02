#! /usr/bin/python

import getopt, sys, pprint, urlparse 
import time as t
from datetime import *
import dateutil.parser
from dateutil.tz import *
#from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost, WordPressComment
from wordpress_xmlrpc.methods import posts, comments
from wordpress_xmlrpc.compat import xmlrpc_client

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:i:b:", ["url=", "user=", "password=", "post_id=", "body="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

# hard coded defaults
url = 'https://x.wordpress.com/xmlrpc.php'
user = None
password = None
post_id = None
body = None

# get commandline options
for o, a in opts:
	if o in ("-x", "--url"):
		url = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a
	elif o in ("-i", "--post_id"):	# csv id(s) of post to add comment
		post_id = a
	elif o in ("-b", "--body"):	# body of comment
		body = a

# get connection to website
try:
	wordpress = Client(url, user, password)
except:
	t.sleep(10)
	try:
		wordpress = Client(url, user, password)
	except:
		t.sleep(10)
		try:
			wordpress = Client(url, user, password)
		except:
			print "Failed to get connection to Wordpress."
			sys.exit(1)

# split list of post ids
post_ids = post_id.split(",")

for post_id in post_ids:

	# check given wordpress post ID exists
	subject_post = None
	if post_id is not None:
		subject_post = wordpress.call(posts.GetPost(post_id))

	# check basic info has been provided
	if body is not None and subject_post is not None:

		# TODO clean up content

		# assemble comment object
		new_comment = WordPressComment()
		new_comment.content = body
		#new_comment.author = 'Whitley Pump'

		# dump out post object
		#pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)
		#pp.pprint(vars(new_comment))

		# Actually post new comment
		new_comment.id = wordpress.call(comments.NewComment(post_id, new_comment))

		# dump out new comment ID
		print new_comment.id
