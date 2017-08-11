#! /usr/bin/python

import getopt, sys, pprint, os.path, mimetypes, urlparse, time
from datetime import *
import dateutil.parser
from dateutil.tz import *
#from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, taxonomies, media
from wordpress_xmlrpc.compat import xmlrpc_client

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:s:t:c:g:d:f:", ["url=", "user=", "password=", "status=", "title=", "content=", "category=", 'date=', 'files='])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

# hard coded defaults
url = 'https://milmanroad.wordpress.com/xmlrpc.php'
user = None
password = None
status = 'draft'
title = None
content = None
categories = None
post_date = None
files = None

# get commandline options
for o, a in opts:
	if o in ("-x", "--url"):
		url = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a
	elif o in ("-s", "--status"):	# status of post; default 'pending'
		status = a
	elif o in ("-t", "--title"):	# title of post
		title = a
	elif o in ("-c", "--content"):	# body of post ([IMG1], [IMG2] will be substituted with proper img HTML for each loaded file -f 'file1, file2')
		content = a
	elif o in ("-g", "--category"):	# CSV list of categories of post
		categories = a
	elif o in ("-d", "--date"):	# date post will be published
		post_date = a
	elif o in ("-f", "--files"): 	# CSV list of FQ filenames of pics on local filesystem to load into WP
		files = a

# get connection to website
try:
	wordpress = Client(url, user, password)
except:
	time.sleep(10)
	try:
		wordpress = Client(url, user, password)
	except:
		time.sleep(10)
		try:
			wordpress = Client(url, user, password)
		except:
			print "Failed to get connection to Wordpress."
			sys.exit(1)

# check basic info has been provided
if title is not None and content is not None:

	# TODO clean up content
	# title plaintext only
	# [more] after first para
	# all pics and links are target=_blank

	# load files into wordpress, if any
	if files is not None and len(files) > 0 :
		filecount=0
		for filename in files.split(','):
			filecount = filecount + 1
			filename = filename.strip()
			if (filename is not None and len(filename) > 0 and os.path.isfile(filename) and os.path.getsize(filename) > 0 ):
				data={}
				data['name'] = os.path.basename(filename)
				data['type'] = mimetypes.guess_type(filename)[0]
				# convert file to base64
				with open(filename, 'rb') as img:
					data['bits'] = xmlrpc_client.Binary(img.read())
				# load file into wordpress
				response = wordpress.call(media.UploadFile(data))
				# substitute picture placeholders in content with WP loaded URL
				if response['url'] is not None:
					parsed_url = urlparse.urlparse(response['url'])
					html_img='<a href=' + response['url'] + ' target=_blank><img class=aligncenter src=' + response['url'] + ' /></a>'
					content = content.replace('[IMG' + str(filecount) + ']', html_img)
			else:
				print "DBG File '" + filename +"' cannot be found."
				sys.exit(1)

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
