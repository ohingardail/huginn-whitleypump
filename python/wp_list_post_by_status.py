#! /usr/bin/python

import getopt, sys, re, json #, pprint
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, users

#pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:s:", ["url=", "user=", "password=", "status="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

url = 'https://x.wordpress.com/xmlrpc.php'
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
	wordpress = Client(url, user, password)
except:
	#print(err)
	sys.exit(1)

# get author name (users.GetUser returns Fault 401: 'Sorry, you are not allowed to edit this user.')
authors = wordpress.call(users.GetAuthors())
def author_name(id):
	if len(authors) > 0:
		for author in authors:
			if author.id == id:
				return author.display_name
# get list of posts
subject_posts = wordpress.call(posts.GetPosts({'post_status': status, 'orderby': 'date', 'order': 'ASC', 'number': 100}))
post_count = len(subject_posts)

if post_count > 0:

	output_events = []
	for subject_post in subject_posts:

		output_event = {}
		output_event['id'] = subject_post.id
		output_event['title'] = subject_post.title.encode('utf-8').replace('"','')
		output_event['date'] = datetime.strftime(subject_post.date, '%d-%b-%Y %H:%M')
		output_event['link'] = subject_post.link
		output_event['author'] = author_name( subject_post.user ).replace('"','')

		# TODO attempt to get true author if listed author is 'Whitley Pump'
		if output_event['author'] == 'Whitley Pump' or output_event['author'] == 'Automation' :
			real_author = re.match('^\s*(?:<i>)?\s*[Bb]y\s+(?:<a .+?>)?([^<\n]+)[<\n\.]', subject_post.content, flags=re.MULTILINE)
			if real_author is not None :
				output_event['author'] = real_author.group(1).encode('utf-8').replace('"','')

		output_events.append(output_event)

	print json.dumps(output_events)
