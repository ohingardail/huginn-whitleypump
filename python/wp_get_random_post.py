#! /usr/bin/python

import getopt, sys, random, json, pprint, re
from datetime import datetime, timedelta
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, users

pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:t:d:e:s:c:", ["url=", "user=", "password=", "tag=", "daysago=", "event=", "size=", "category="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

url = 'https://milmanroad.wordpress.com/xmlrpc.php'
user = None
password = None
tag = None # 'Specials' # category of post to choose from
daysago = None # 6 * 30 # posts must be older than this
event = None # when this program receives event to pass on downstream
size = None
category = None

for o, a in opts:
	if o in ("-x", "--url"):
		url = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a
	elif o in ("-t", "--tag"):
		tag = a
	elif o in ("-d", "--daysago"):
		daysago = a
	elif o in ("-e", "--event"):
		event = a	
	elif o in ("-s", "--size"):
		size = a		
	elif o in ("-c", "--category"):
		category = a	

# get connection to website
try:
	wordpress = Client(url, user, password)
except:
	print "Unable to access Wordpress"
	sys.exit(1)

# get author name (users.GetUser returns Fault 401: 'Sorry, you are not allowed to edit this user.')
authors = wordpress.call(users.GetAuthors())
def author_name(id):
	if len(authors) > 0:
		for author in authors:
			if author.id == id:
				return author.display_name

# get list of published posts (in batches)
offset = 0
increment = 20
published_posts = []
while True:
        returned_posts = wordpress.call(posts.GetPosts({'post_type':'post', 'post_status':'publish', 'number':increment, 'offset':offset}))
        if len(returned_posts) == 0:
                break  # no more posts returned
        for returned_post in returned_posts:
                published_posts.append(returned_post)
        offset = offset + increment

# make subselection of posts
candidate_posts1 = []
candidate_posts2 = []
candidate_posts3 = []
if len(published_posts) > 0:
	for published_post in published_posts:
		#pp.pprint(vars(published_post))
		
		# extract posts published more than daysago days ago (or all posts, if daysago undefined)
		# and which are over the specified size
		if 	(daysago is None or len(daysago) == 0 or published_post.date < (datetime.today() - timedelta(days=int(daysago))) ) \
		and 	(size is None or len(size) == 0 or int(size) == 0 or len(published_post.content) >= int(size) ):
			#pp.pprint(vars(published_post))
			candidate_posts1.append(published_post)

# extract posts with the specified tag (eg 'Specials')
if tag is not None and len(tag) > 0 :
	for candidate_post1 in candidate_posts1:
		for term in candidate_post1.terms:
			if term.taxonomy == 'post_tag' and term.name.lower() == tag.lower():
				candidate_posts2.append(candidate_post1)
else:
	candidate_posts2 = candidate_posts1

# extract posts with the specified category (eg 'Katesgrove ward')
if category is not None and len(category) > 0 :
	for candidate_post2 in candidate_posts2:
		for term in candidate_post2.terms:
			if term.taxonomy == 'category' and term.name.lower() == category.lower():
				candidate_posts3.append(candidate_post2)
else:
	candidate_posts3 = candidate_posts2

# pick a candidate post at random	
if len(candidate_posts3) > 0:	
	candidate_post = candidate_posts3[random.randint(0, len(candidate_posts3)-1)]
	# pp.pprint(vars(candidate_posts3))
	
	# append results to input event, if it exists
	output_event = {}
	if event is not None and len(event) > 0:
		output_event = json.loads(event.replace('\\"','"'))

	output_event['title'] = candidate_post.title.encode('utf-8')
	output_event['content'] = candidate_post.content.encode('utf-8')
	output_event['link'] = candidate_post.link
	output_event['author'] = author_name( candidate_post.user )

	# print out event as string (to be deserialized by downstream function)
	print json.dumps(output_event)
	
