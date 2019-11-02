#! /usr/bin/python
import getopt, sys, pprint, os.path, mimetypes, urlparse, re, requests, json, uuid, PIL, base64

# time stuff
from datetime import datetime, timedelta
import time as t
from datetime import *
import dateutil.parser
from dateutil.tz import *

pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "u:a:s:t:c:w:g:t:d:i:", ["url=", "authorisation=", "status=", "title=", "content=", "author=", "categories=", "tags=", "date=", "images="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

# hard coded defaults
url = None # 'https://whitleypump.net/wp-json/wp/v2/'
authorisation = None 
status = 'draft'
title = None
content = None
categories = None
tags = None
author = None
post_date = (datetime.today() + timedelta(days=7)).strftime('%F 12:00:00') # one week hence
images = None
max_filesize = 1048576/2 # max picture filesize (500Kb)

# get commandline options
for o, a in opts:
	if o in ("-u", "--url"):
		url = a
	elif o in ("-a", "--authorisation"):
		authorisation = a
	elif o in ("-s", "--status"):	# status of post; default 'pending'
		status = a
	elif o in ("-t", "--title"):	# title of post
		title = a
	elif o in ("-c", "--content"):	# body of post ([IMG1], [IMG2] will be substituted with proper img HTML for each loaded file -f 'file1, file2')
		content = a
	elif o in ("-w", "--author"):	# author
		author = a
	elif o in ("-g", "--categories"):	# CSV list of categories of post
		categories = a
	elif o in ("-t", "--tags"):	# CSV list of tags of post
		tags = a
	elif o in ("-d", "--date"):	# date post will be published
		post_date = a
	elif o in ("-f", "--images"): 	# CSV list of FQ filenames of pics on local filesystem to load into WP
		images = a

# standardised wordpress rest api call
# returns 'content' as JSON
# deals with pagination
# POST and GET only
# TODO : PUT
# eg wp_rest('get', 'settings', None, None)
# eg wp_rest('post', 'post', {...}, None)
# eg wp_rest('post', 'media', {...}, {...})
# note: rest api arg 'search' is unpredicatable (prob pagination)
def wp_rest(request_type, endpoint, data_in, header_in) :

	#print "DBG: wp_rest(" + request_type + "," + endpoint

	# init
	attempt = 1 # first attempt
	max_attempts = 3 # number of attempts to make
	retry_delay = 10 # secs
	per_page = 50 # recs to return in one call
	contents = None

	# request_type and endpoint are mandatory
	if request_type == None or endpoint == None or len(request_type) == 0 or len(endpoint) == 0 :
		print "ERR: No request type or endpoint specified."
		sys.exit(1)
	else :
		request_type = request_type.lower()
		endpoint = endpoint.lower()

	# if specified, header must be non-empty dicts
	if header_in is not None and len(header_in) > 0 and not isinstance(header_in, dict) :
		print "ERR: custom headers must be a Python 'dict' object but is actually '" + str(type(header_in)) + "'"
		sys.exit(1)

	# set headers
	header = { 	'user-agent': 'huginn-whitleypump', \
			'authorization'	: 'Bearer ' + authorisation  \
			#'content-type'	: 'application/json' \
		}

	# append userdef headers (like media filename)
	if header_in is not None :
		header.update(header_in)
	
	# data_in must be binary in media posts
	if request_type == 'post' and endpoint == 'media' :

		if data_in is not None and not isinstance(data_in, file) :
			print "ERR: payload must be a Python 'file' (binary) object but is actually '" + str(type(data_in)) + "'"
			sys.exit(1)

		header.update({ "cache-control" : "no-cache" })

		if not ("content-disposition" in header and "content-type" in header ) :
			print "ERR: header must contain 'content-disposition' and 'content-type'."
			sys.exit(1)
	else:

		if data_in is not None and len(data_in) > 0 and not isinstance(data_in, dict) :
			print "ERR: payload must be a Python 'dict' object but is actually '" + str(type(data_in)) + "'"
			sys.exit(1)

	#if request_type == 'post' and endpoint == 'posts' :
	#	print "DBG:" + str(request_type) + " " + str(url) + str(endpoint) + " " + str(data_in) + "."
	#	response = requests.post(url + endpoint, headers=headers, data=data_in)
	#	pp.pprint(vars(response))
	#	sys.exit(1)
			
	#print "DBG: header = " + str(header)
	#print "DBG: data = " + str(data_in)

	# for each type of request, loop:
	if request_type.lower() == 'get' :

		contents = []
		page = 1
		total_pages = 1
	
		while True:

			#print "DBG: page " + str(page) + " of " + str(total_pages) + "."
			success = True
			full_url = url + endpoint + '?per_page=' + str(per_page) + '&page=' + str(page)

			if data_in is None :
				while attempt < max_attempts :
					try:
						response = requests.get( full_url, headers=header )
					except:
						attempt = attempt + 1
						success = False
						t.sleep(retry_delay)
						continue
					break
			else :
				while attempt < max_attempts :
					try:
						response = requests.get( full_url, headers=header, data=data_in )
					except:
						attempt = attempt + 1
						success = False
						t.sleep(retry_delay)
						continue
					break

			# check if it worked (success and 2nn http status code)
			if success and re.search(r'2\d{2}', str(response.status_code)) :

				# append page contents
				if len(contents) == 0 :
					contents = json.loads(response.content)
				else:
					contents.extend(json.loads(response.content))

			elif attempt >= max_attempts:
				try:
					print "ERR " + str(response.status_code) + \
						": Unable to " + request_type + " data at REST API at '" + full_url + \
						'?per_page=' + str(per_page) + '&page=' + str(page) + \
						"' after " + str(attempt) + " attempts."
				except:
					print "ERR: Unable to " + request_type + " data at REST API at '" + full_url + \
						'?per_page=' + str(per_page) + '&page=' + str(page) + \
						"' after " + str(attempt) + " attempts."
				pp.pprint(vars(response))
				sys.exit(1)


			# only know the real number of pages and records after first page retrieved
			if page == 1: 
				#print "DBG: " + str(response.headers)

				try:
					total_pages = int(response.headers['X-WP-TotalPages'])
				except:
					total_pages = 1
				try:	
					total_records = int(response.headers['X-WP-Total'])
				except:
					total_records = None
	
			# end loop
			if page >= total_pages :
				break
			
			# prepare for next loop
			page = page + 1

		# check expected records
		if total_records is not None and len(contents) != total_records:
			print "ERR: expected " + str(total_records) + " but received " + str(len(contents)) + " from '" + request_type + "' at '" + url + "'."

	elif request_type.lower() == 'post' :

		success = True
		full_url = url + endpoint

		if data_in is None :
	
			while attempt <= max_attempts :
				try:
					response = requests.post(full_url, headers=header)	
				except:
					attempt = attempt + 1
					success = False
					t.sleep(retry_delay)
					continue
				break
		else :

			while attempt <= max_attempts :
				try:
					response = requests.post(full_url, headers=header, data=data_in)		
				except:
					attempt = attempt + 1
					success = False
					t.sleep(retry_delay)
					continue
				break

	elif request_type.lower() == 'put' :

		success = True
		full_url = url + endpoint

		if data_in is None :
	
			while attempt <= max_attempts :
				try:
					response = requests.put(full_url, headers=header)	
				except:
					attempt = attempt + 1
					success = False
					t.sleep(retry_delay)
					continue
				break
		else :

			while attempt <= max_attempts :
				try:
					response = requests.put(full_url, headers=header, data=data_in)		
				except:
					attempt = attempt + 1
					success = False
					t.sleep(retry_delay)
					continue
				break
	else:
		attempt = 0		
		success = False
		print "ERR: request type '" + request_type + "' unsupported."
		return None

	# check errors (for non-gets)(success and 2nn http status code)
	if success and re.search(r'2\d{2}', str(response.status_code)) :

		if contents is None or len(contents) == 0 :
			contents = json.loads(response.content)

	else:
		try:
			print "ERR " + str(response.status_code) + \
				": Unable to " + request_type + " data at REST API at '" + full_url + \
				"' after " + str(attempt) + " attempts."
		except:
			print "ERR: Unable to " + request_type + " data at REST API at '" + full_url + \
				"' after " + str(attempt) + " attempts."
		pp.pprint(vars(response))
		sys.exit(1)

	#print "DBG: contents = " + str(contents)
	#pp.pprint(vars(response))
	return contents

# end def wp_rest

# check url available and auth working
def check_connection():

	# settings only work for admin users
	#settings = wp_rest('get', 'settings', None, None )
	#print "DBG: settings = '" + str(settings) + "'."
	#blog_title = settings['title']
	#print "DBG: blog_title = '" + blog_title + "'."
	#default_user =
	#if blog_title is None or blog_title != 'The Whitley Pump' :
	#	print "ERR: Unexpected blog title '" + blog_title + "'."
	#	sys.exit(1)
	settings = wp_rest('get', 'users/me', None, None )
	user_name = settings['name']
	if user_name is None or user_name != 'The Whitley Pump' :
		print "ERR: Unexpected user name '" + user_name + "'."
		sys.exit(1)

# end def validate

# converts csv list of names into csv list of ids
def get_categories(categories):

	#print "DBG: get_categories(" + categories + ")"

	category_id = []
	source_categories = wp_rest('get', 'categories', None, None)
	search_categories = categories.split(',')

	#print "DBG: #source_categories=" + str(len(source_categories))
	#print "DBG: #search_categories=" + str(len(search_categories))

	for source_category in source_categories :
		for search_category in search_categories :
			source_category_name = source_category['name'].replace('&amp;','and').replace('&','and').strip().lower()
                        search_category_name = search_category.replace('&amp;','and').replace('&','and').strip().lower()
                        if source_category_name == search_category_name :
				#print "DBG: " + source_category['name'] + " = " + search_category
				category_id.append( str(source_category['id']) )
                		break
	return ','.join(category_id)

# end def get_categories

# converts csv list of names into csv list of ids
def get_tags(tags):

	#print "DBG: get_tags(" + tags + ")"

	tag_id = []
	source_tags = wp_rest('get', 'tags', None, None)
	search_tags = tags.split(',')

	for source_tag in source_tags :
		for search_tag in search_tags :
			source_tag_name = source_tag['name'].replace('&amp;','and').replace('&','and').strip().lower()
                        search_tag_name = search_tag.replace('&amp;','and').replace('&','and').strip().lower()
                        if source_tag_name == search_tag_name :
				#print "DBG: " + source_tag['name'] + " = " + search_tag
				tag_id.append( str(source_tag['id']) )
				break
	return ','.join(tag_id)

# end def get_tags

# converts author name to ID (default current user)
# standard 'editor' permissions cause request (and script) to fail
def get_author(author):

	#print "DBG: get_author(" + author + ")"
	
	source_users = wp_rest('get', 'users', None, None)
	found_user = None
	for source_user in source_users :
		if source_user['name'].strip().lower() == author.strip().lower() :
			found_user = source_user
			break
	# default
	if found_user == None:
		found_user = wp_rest('get', 'users/me', None, None)

	#print "DBG: user = '" + str(found_user) + "'."
	return found_user['id']

# end def get_author

# post a wp post
# date should be a string delivered in form '2019-08-03 20:00:00' (or None)
def post_post(title, content, author, categories, tags, datestring, status):

	#print "DBG: post_post(" + title + "," + content + "," # + author + "," + categories + "," + tags + "," + datestring + "," + status + ")"

	# only continue if there's something to do!
	#if title is not None and content is not None and len(title.replace(' ', '')) > 0 and len(content.replace(' ', '')) > 0 :

	# validate status
	if status is None or (status.strip() != 'draft' and status.strip() != 'pending'):
		status = 'draft'

	# validate date (default to midday 1 week hence)
	if datestring is not None and len(datestring.strip()) > 0 :
		# check it can be parsed as a date
		try:
			dateObj = dateutil.parser.parse(datestring)
		except:
			dateObj = None

	if dateObj is None :
		dateObj = dateutil.parser.parse((datetime.today() + timedelta(days=7)).strftime('%FT12:00:00'))

	data = { \
		"format"	: "standard", 		\
		"status"	: status.strip(), 	\
    		"title"		: title.strip(), 	\
		"date"		: dateObj.strftime('%FT%T')\
		}

	# process categories, if any
	if categories is not None and len(categories.replace(' ', '')) > 0 :
		data['categories'] = get_categories(categories)

	# process tags, if any
	if tags is not None and len(tags.replace(' ', '')) > 0 :
		data['tags'] = get_tags(tags)

	# add refs to recently loaded images, if any
	data['content'] = content.strip()

	# update authorship
	#if author is not None and len(author.replace(' ', '')) > 0 :
	#	data['author'] = get_author(author)
	
	#data['author'] = 2
	
	print "DBG: post = " + str(data)
	response = wp_rest('post', 'posts', data, None)
	post_id = response['id']
	#print "DBG: response = " + str(response)

	# return id of newly created post
	return post_id

# end def post_post

# loads (csv string list of) files and returns array containing their ids
# todo - find media assoc with text if not file
def load_images(title, files) :

	#print "DBG: load_files(" + title + "," + images + ")"

	media_id = []

	# load files into wordpress, if any
	#if files is not None and len(files) > 0 :

	filecount=0

	for filex in files.split(',') : 

		filecount = filecount + 1
		filename = filex.strip()
		filesize = os.path.getsize(filename)
		filetype = mimetypes.guess_type(filename)[0]
		filebasename, fileextension = os.path.splitext(filename)
		newfilename = uuid.uuid4().hex + fileextension

		if (filename is not None and len(filename) > 0 and os.path.isfile(filename) and filesize > 0 ):	

			# load file
			header =  	{ \
					'content-type': filetype, \
					'content-disposition': 'attachment; filename=' + newfilename \
					}
			
			with open(filename, 'rb') as imagefile:
				response = wp_rest('post', 'media', imagefile, header)	

			# update media title etc
			if title is not None and response['id'] is not None :
				data = { \
					"title"		: title.strip(), 		\
					"alt_text"	: title.strip(), 		\
					"description"	: 'Image (c) the Whitley Pump', 	\
					}
				response = wp_rest('put', 'media/' + str(response['id']), data, None)

			media_id.append(str(response['id']))
		else:
			#print "DBG File '" + filename +"' cannot be found or contained no data."
			sys.exit(1)

	return ','.join(media_id)

# end def load_files

##### MAIN ######

# if there is anything to do...
if title is not None and content is not None and len(title.replace(' ', '')) > 0 and len(content.replace(' ', '')) > 0 :

	# check connection
	check_connection()

	# load files, if any
	if images is not None and len(images) > 0 :
		media_ids = load_images(title, images)
		#media_ids = "123,456,789"
	
		# convert [IMGn] placeholder in post text to galleries
		filecount = 0
		for media_id in media_ids.split(',') :
			filecount = filecount + 1
			#htmlimage='[gallery type="rectangular" size="full" ids="' + media_id + '"]'
			content = re.sub('\\bIMG' + str(filecount) + '\\b', media_id, content)
		
		content = re.sub('\[([\d\s,]+)\](<br\s*/*>)*', '[gallery type="rectangular" size="full" ids="\\1"]<br><br>', content)
		# print "DBG: content=" + content

	# load post
	post_id = post_post(title, content, author, categories, tags, post_date, status)

	# dump out new post ID
	print post_id

