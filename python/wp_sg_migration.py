#! /usr/bin/python
import getopt, sys, pprint, os, mimetypes, urlparse, re, requests, PIL, math, base64
import time as t
import dateutil.parser
import MySQLdb # possible backup updater
from PIL import Image
from dateutil.tz import *
from datetime import datetime, timedelta
#from datetime import *
from wordpress_xmlrpc import Client, WordPressPost, WordPressComment, WordPressMedia
from wordpress_xmlrpc.methods import posts, taxonomies, media, users, comments, demo
from wordpress_xmlrpc.compat import xmlrpc_client

# Hmmm - 'image = image.resize( (new_width,new_height), Image.ANTIALIAS )' failed 'IOError: image file is truncated (0 bytes not processed)'
#from PIL import ImageFile
#ImageFile.LOAD_TRUNCATED_IMAGES = True

# confgure prettyprinter (for debug only)
pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)

# Wordpress connection parameters
source_url = 'https://source/xmlrpc.php'
source_user = ''
source_password = ''
sink_url = 'https://sink/xmlrpc.php'
sink_user = ''
sink_password = ''

# sink mysql connection parameters
# REMEMBER TO ALLOW / DISALLOW MYSQL ACCESS TO SITEGROUND TO CURRENT EXTERNAL IP!
mysql_user = ''
mysql_password = ''
mysql_server = '' # You get this from SITEGROUND - ACCOUNT DNS
mysql_database = ''

# folder and file locations
data_folder = './siteground_migration/'
media_folder =  data_folder + 'media/'
comments_file = data_folder + 'comments.csv' # list of (correctly formed!) comments to import via MySQL
pages_map_file = data_folder + 'pages_map.csv' # list of page parentage
posts_map_file = data_folder + 'posts_map.csv' # list of migrated posts
media_map_file = data_folder + 'media_map.csv' # list of migrated media files

# other values
default_status = 'draft'
max_filesize = 1048576/2 # max picture filesize (500Kb)
max_connection_attempts = 3
#max_loops = 10 # set within func instead
increment = 10 # num of items to process in one loop (to reduce server load)
source_domain = source_url.split('/')[2]
sink_domain = sink_url.split('/')[2]

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "d", ['debug'])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

# get commandline options
for o, a in opts:
	if o in ("-d", "--debug"):	# debug flag
		debug = true


##### USERDEF FUNCTIONS ######

# basic string cleanup (titles etc)
def basic_cleanup(string):

	if string is None or len(string) == 0 :
		return None

	# fix non-standard quotes
	string = re.sub('[\x93\x94]', 			"'", 	string)
	string = re.sub(ur'[\u201c\u201d]', 		"'", 	string)
	string = re.sub('[\x91\x92]', 			"'", 	string)	
	string = re.sub(ur'[\u2018\u2019\u201b]', 	"'", 	string)
	# remove (c) symbol
	#string = re.sub('[\xa9]', 			"(c)",	string)
	#string = re.sub('[\x40]', 			"(a)",	string)
	# remove cntrl characters
	#string = re.sub('[[:cntrl:]])', 		' ',	string)
	# remove html
	string = re.sub('<.*?>', 			'',	string)
	# convert '&' to 'and' (html entity shows up in FB/TW
	string = re.sub('&amp;', 			'and',	string)
	# fix non-standard or repeating spaces
	string =string.replace(unichr(160), " ")
	string = re.sub(' +', 				' ', 	string)

	return string

# major string cleanup (content etc)
def major_cleanup(string):

	if string is None or len(string) == 0 :
		return None

	# replace non-standard quotes with "\x22" or 'x27'
	string = re.sub('[\x93\x94]', 				'"',string)
	string = re.sub(ur'[\u201c\u201d]', 			'"',string)
	string = re.sub('[\x91\x92]', 				"'",string)	
	string = re.sub(ur'[\u2018\u2019\u201b]', 		"'",string)

	# replace doubled-up quotes unless preceded with '='
	string = re.sub('(?<!=)([\'\"])\\1', 			'\\1',string)

	# replace doubled-up quotes unless preceded with '='
	string = re.sub('(?<!=)([\'\"])\\1', 			'\\1', string)

	# remove redundant div tags
	#string = re.sub('</?div.*?>', '', string)
	string = re.sub('<div>(.*?)</div>', 			'\\1', string, flags=re.DOTALL)
	string = re.sub('<div\s+id=".*?"\s*>(.*?)</div>', 	'\\1', string, flags=re.DOTALL)
	string = re.sub('<div\s+lang=".*?"\s*>(.*?)</div>', 	'\\1', string, flags=re.DOTALL)
	string = re.sub('<div\s+class=".*?"\s*>(.*?)</div>', 	'\\1', string, flags=re.DOTALL)

	# remove redundant span tags
	#string = re.sub('</?span.*?>', '', string)
	string = re.sub('<span>(.*?)</span>', 			'\\1', string, flags=re.DOTALL)
	string = re.sub('<span\s+id=".*?"\s*>(.*?)</span>', 	'\\1', string, flags=re.DOTALL)
	string = re.sub('<span\s+lang=".*?"\s*>(.*?)</span>', 	'\\1', string, flags=re.DOTALL)
	string = re.sub('<span\s+class=".*?"\s*>(.*?)</span>', 	'\\1', string, flags=re.DOTALL)
	string = re.sub('<span\s+style=".*?"\s*>(.*?)</span>', 	'\\1', string, flags=re.DOTALL)

	# remove redundant p tags
	string = re.sub('<p>(.*?)</p>', 			'\\1<br>', string, flags=re.DOTALL)
	string = re.sub('<p\s+id=".*?"\s*>(.*?)</p>', 		'\\1<br>', string, flags=re.DOTALL)
	string = re.sub('<p\s+lang=".*?"\s*>(.*?)</p>', 	'\\1<br>', string, flags=re.DOTALL)
	string = re.sub('<p\s+class=".*?"\s*>(.*?)</p>', 	'\\1<br>', string, flags=re.DOTALL)

	# remove redundant <br id> tags
	string = re.sub('<br\s+id=".*?"\s*/> ', 		'\n', string)

	# Make sure sentence starts are capitalised

	# make ellipses standard
	string = re.sub('\.{2,}', 				'... ', string)

	# remove duplicated punctuation
	string = re.sub('(&amp;){2,}', 				'\\1', string) # &&
	string = re.sub('([\(\)]){2,}', 			'\\1', string) # (( )) () )( -> first one
	string = re.sub('([!?,:;$]){2,}', 			'\\1', string) # !?,:;%$- followed by any one of that set again
	string = re.sub('[!?,:;]\.', 				'.',   string) # !. ?. ,. :. ;. -. -> .
	string = re.sub('\.([!?,:;])', 				'\\1', string) # as above, but reversed -> first one

	# make sure "xxx ," doesnt happen
	string = re.sub('\\b(\w+)\s+,\s?', 			'\\1, ', string)

	# ensure all links open in new page
	string = re.sub(\
		'<(a(?=\s+|>)(?!(?:[^>=]|=([\'\"])(?:(?!\\2).)*\\2)*?\s+target=)[^>]*)>(?!\s*<\s*img\\b)', \
		'<\\1 target="_blank">', \
		string)

	# ensure all internal links (aka bookmarks with href="#abc") *dont* open in new page
	string = re.sub('<a(?=\s+|>)\s+(href=([\'\"])#(?:(?!\\2).)*\\2)(.*?)>','<a \\1>', string)

	# fixed duplicated hrefs (where post has mix of linked and unlinked pics)
	string = re.sub(\
		'(<a href=".*?" .*?>)(<a href=".*?" .*?>)(<img .*? \/>)(<\/a><\/a>)', \
		'\\2\\3</a>', \
		string)

	# fix common spelling errors TODO esc URLs
	#string = re.sub('\\b(?<![[:punct:]])([Cc])llr\\b', 	'\\1ouncillor', string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])(t)hr\\b', 		'\\1he', 	string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])(d)ont\\b', 		'\\1on\'t', 	string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])(d)idnt\\b', 	'\\1idn\'t', 	string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])(c)ouldnt\\b', 	'\\1ouldn\'t', 	string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])uk(\'s)?\\b', 	'UK\\1', 	string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])mp(\'s)?\\b', 	'MP\\1', 	string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])europe(.*?)\\b',	'Europe\\1', 	string, flags=re.IGNORECASE)
	#string = re.sub('\\b(?<![[:punct:]])kategrove\\b',	'Katesgrove', 	string, flags=re.IGNORECASE)

	# remove double lines
	string = re.sub('(\n\s*){2,}', r'\n\n', 			string, flags=re.MULTILINE)

	# remove double spaces
	string = string.replace(unichr(160), " ")
	string = re.sub(' +', ' ', string) # \s also collapses newlines

	# remove initial blank line (this can remove *all* blank lines)
	string = re.sub('\A(?: |&nbsp;|\n)*(.*)', '\\1', string, flags=re.MULTILINE)

	# correctly form initial byline (if any)
	string = re.sub('\A(?:<em>)?\s*(By\\b.*?)[\.\s]*(?:<\/em>)?\n', '<em>\\1.</em>\n', string, flags=(re.IGNORECASE | re.MULTILINE))	
				
	# remove terminal blank line
	string = re.sub('(.*)(?: |&nbsp;|\n)*\Z', '\\1', string, flags=re.MULTILINE)

	# add more line after first para, if one not already included
	if not re.search('<!--more-->', string, re.IGNORECASE):
		string = re.sub('^(<a[^\n]+</a>\n+[^\n]+)\n*', '\\1\n\n<!--more-->\n', string, count=1, flags=re.MULTILINE)
	
	# make sure more line is correctly spaced
	string = re.sub('(?:(<br ?/? ?>|\n))*<(?:!-*)?more(?:-*)?>(?:(<br ?/? ?>|\n))*', r'\n\n<!--more-->', string, flags=re.MULTILINE)

	# Headify Links header
	string = re.sub('<hr ?\/? ?>\n+Links ?\n+', '<hr />\n<h5>Links</h5>\n', string, flags=re.MULTILINE)

	return string

# calls specified sql and returns result
# result is a LIST containing data tuples (ie rows)
# example : 
# DATA_START>  [
# ROW_1>        (u'violent crime', Decimal('124'), Decimal('220'), Decimal('253')), 
# ROW_2>        (u'anti social behaviour', Decimal('250'), Decimal('262'), Decimal('221'))
# DATA_END>    ]
# print resultset(0) - column names (as one tuple)
# print resultset(1) - all data rows (as a list of tuples)
def mysql_sql(db_object, query):
	if query is None:
		print "ERR: mysql_sql : must specify query"
		return None
	# print "DBG: query = " + query
	#resultset = []
	db_cursor = db_object.cursor()
	try:
		db_cursor.execute(query)
	except:
		print 'ERR: mysql_sql query "' + query + '" failed.'
		return None
	#resultset.append(zip(*mysql_sql.description)[0])
	resultset = db_cursor.fetchall()
	#print resultset
	db_cursor.close()
	if resultset is not None:
		return resultset
	return None

# get connection to wordpress
def connect_wordpress(url, user, password):
	connection_attempt = 0
	while connection_attempt <= max_connection_attempts :
		try:
			wordpress_object = Client(url, user, password)
		except:
			wordpress_object = None
		connection_attempt = connection_attempt + 1	
		if wordpress_object == None :
			if connection_attempt < max_connection_attempts :
				t.sleep(10)
			else:
				print "ERR: Failed to connect to Wordpress at '" + url + "'."
				sys.exit(1)
	print "INF: Connected to Wordpress at '" + url + "'." 
	return wordpress_object

# wordpress connection check
def check_connection(wordpress_object, url, user, password):
	connection_attempt = 0
	while connection_attempt <= max_connection_attempts :
		try:
			wordpress_object.call(demo.SayHello())
		except:
			wordpress_object = connect_wordpress(url, user, password)
		connection_attempt = connection_attempt + 1
		if wordpress_object == None :
			if connection_attempt < max_connection_attempts :
				t.sleep(30)
			else:
				print "ERR: Failed to reconnect to Wordpress at '" + url + "'."
				sys.exit(1)
	return wordpress_object

# get connection to WP database
# only enable if required - dangerous! requires special config (SITEGROUND needs to know current external IP of client)!
def connect_db(user, password, server, database):
	connection_attempt = 0
	while connection_attempt <= max_connection_attempts :
		try:
			db_object = MySQLdb.connect(user = mysql_user, passwd = mysql_password, host = mysql_server, db = mysql_database)
		except:
			db_object = None
		connection_attempt = connection_attempt + 1	
		if db_object == None :
			if connection_attempt < max_connection_attempts :
				t.sleep(30)
			else:
				print "ERR: Failed to connect to database at '" + mysql_server + "." + mysql_database + "'."
				sys.exit(1)
	db_object.autocommit(True)
	print "INF: Connected to database at '" + mysql_server + "." + mysql_database + "'."
	return db_object

# db connection check
def db_check_connection(db_object, user, password, server, database):
	connection_attempt = 0
	while connection_attempt <= max_connection_attempts :
		try:
			mysql_sql(db_object,'select count(*) from wp_posts')
		except:
			db_object = connect_db(user, password, server, database)
		connection_attempt = connection_attempt + 1
		if wordpress_object == None :
			if connection_attempt < max_connection_attempts :
				t.sleep(30)
			else:
				print "ERR: Failed to reconnect to database at '" + mysql_server + "." + mysql_database + "'."
				sys

####### MIGRATE MEDIA #########
	#wordpressmedia
	#parent
	#title
	#description
	#caption
	#date_created (datetime)
	#link
	#thumbnail
	#metadata
def migrate_media(medium_id):

	max_loops = 10000

	migrated_media = []
	with open(media_map_file) as media_map:  
	   for count, line in enumerate(media_map):
	       migrated_media.append(line.split(',')[0].strip('"'))

	# get a list of all media (in batches, to avoid server overload)
	#offset = len(migrated_media)
	offset = 0
	migrated_media_count = 0
	loops = 0
	while True:
		if medium_id is None:
			print "INF: extracting next " + str(increment) + " media items from source library starting at item " + str(offset) + "..."
			
			# keep trying until connection made
			while True :
				try:
					source_media = source_wordpress.call(media.GetMediaLibrary({'number': increment, 'offset': offset}))
				except:
					check_connection(source_wordpress, source_url, source_user, source_password)
					continue
				break
		else:
			# debug only - pick one medium to load
			source_media = []
			source_media.append(source_wordpress.call(media.GetMediaItem(medium_id)))
			max_loops = 1 # force next loop fail after this loop

		# if no more posts returned (or debug limit reached), then stop
		if len(source_media) == 0 or loops >= max_loops :
			break

		# for each post in the source list...
		for source_medium in source_media:

			# vars to hold working data
			media_migration_record = []

			# if we have no record the medium has already been migrated...
			#if source_medium.id not in 'x': # DEBUG force reloading of same image
			if source_medium.id not in migrated_media: 

				print "INF: Migrating medium '" + source_medium.id + "'..."

				#print "DBG: initial source medium post= "
				#debug_medium 	= source_wordpress.call(posts.GetPost(source_medium.id))
				#pp.pprint(vars(debug_medium))
				#print "DBG: initial source medium = "
				#pp.pprint(vars(source_medium))

				# keep tally of work done
				media_migration_record.append('"' + source_medium.id + '"')
				media_migration_record.append('"' + source_medium.link + '"')

				# extract picture
				try:
					filename = media_folder + os.path.basename(source_medium.metadata['file'])
				except:
					filename = media_folder + os.path.basename(source_medium.link)
				filehandle = open(filename, "wb")
				while True :
					try:
						filehandle.write(requests.get(source_medium.link).content)
					except:
						t.sleep(30)
						continue
					break
				filehandle.close()
				filetype = mimetypes.guess_type(filename)[0]
				#try:
				#	filesize = source_medium.metadata['filesize'] # not always available
				#except:
				filesize = os.path.getsize(filename)
				#print "DBG: filesize = " + str(filesize)
				#print "DBG: filetype = " + filetype

				# only attempt to resize images
				if filetype == 'image/jpeg' or filetype == 'image/jpg' or filetype == 'image/png' :

					image = Image.open(filename)
					biggest_dim = max(image.size[0], image.size[1])

					# check picture size and make <= 900px max dim
					if biggest_dim > 900 :
						proportion = 900/float(biggest_dim)
						image = image.resize( ( int(round(image.size[0] * proportion)), int(round(image.size[1] * proportion)) ), Image.ANTIALIAS )
						print "INF: Resized medium '" + filename + "' to " + str(round(proportion * 100)) + "% to keep within 900px."
					if filesize > max_filesize :
						if biggest_dim <= 900 :
							proportion = round(float(max_filesize)/float(filesize),1)
							if proportion > 2:
								proportion = 0.8
							else:
								proportion = 0.9
							image = image.resize( ( int(round(image.size[0] * proportion)), int(round(image.size[1] * proportion)) ), Image.ANTIALIAS )
							print "INF: Resized medium '" + filename + "' to " + str(round(proportion * 100)) + "% to reduce filesize."

					#print "DBG: image.format = '" + image.format + "'"
					#print "DBG: image.size[0] = '" + str(image.size[0]) + "'"
					#print "DBG: image.size[1] = '" + str(image.size[1]) + "'"

					# try to compress image further...
					image.save(filename, optimize=True, quality=95)
					#print "INF: Resized medium '" + filename + "'."			

					# close image file
					image.close()

				# convert file to bits
				with open(filename, 'rb') as binfile:
					base_64_instance = xmlrpc_client.Binary(binfile.read())
				
				# debug
				#pp.pprint(vars(base_64))
				#print "DBG: len(base_64_instance.data) = " + str( len(base_64_instance.data) )
				#base_64_instance.data = base64.b64decode( base64.b64encode( base_64_instance.data ) + '===')
				#bin_debug = open(media_folder + 'bin_' + os.path.basename(filename), "wb")
				#bin_debug.write(base_64_instance.data)
				#bin_debug.close()
				#print "DBG: bin_debug(filesize)= " + str(os.path.getsize(media_folder + 'bin_' + os.path.basename(filename)) )
				#sys.exit(1)

				# construct upload object
				data = {
					'name': os.path.basename(filename),
					'type': filetype,
					'bits': base_64_instance,
					'overwrite': False
				}
				#print "DBG: len(data['bits'].data) = " + str( len(data['bits'].data) )

				# upload medium to sink site
				#migrated_medium = sink_wordpress.call(media.UploadFile(data))
				#pp.pprint(vars(migrated_medium))
				#sys.exit(1)

				# avoid known errored loads (27383 fails to load properly, causing endless retries)
				#if source_medium.id not in ['27383']:
				if source_medium.id not in ['X']:

					while True :
						try:
							migrated_medium = sink_wordpress.call(media.UploadFile(data))
						except:
							check_connection(sink_wordpress, sink_url, sink_user, sink_password)
							continue
						break

					# update relevant attachment post with correct description, caption and date_created
					while True :
						try:
							attachment_post = sink_wordpress.call(posts.GetPost(migrated_medium['id']))
						except:
							check_connection(sink_wordpress, sink_url, sink_user, sink_password)
							continue
						break

					#print "DBG: uploaded (uncorrected) source medium post= "
					#pp.pprint(vars(attachment_post))
					attachment_post.title 	= basic_cleanup(source_medium.title)
					attachment_post.content = basic_cleanup(source_medium.description)
					attachment_post.excerpt = basic_cleanup(source_medium.caption)
					attachment_post.date 	= source_medium.date_created 
					
					# this buggers up thumbnails; run 'wp media regenerate --yes' on server cli to fix (currently scheduled for overnight)
					while True :
						try:
							sink_wordpress.call(posts.EditPost(migrated_medium['id'], attachment_post))
						except:
							check_connection(sink_wordpress, sink_url, sink_user, sink_password)
							continue
						break

					# keep tally of work done
					media_migration_record.append('"' + migrated_medium['id'] + '"')
					media_migration_record.append('"' + migrated_medium['url'] + '"')

					# store description and caption for later use (to be updated via mysql)
					#media_migration_record.append('"' + cleanup(source_medium.description) + '"')
					#media_migration_record.append('"' + cleanup(source_medium.caption) + '"')
					#media_migration_record.append('"' + source_medium.date_created.strftime('%Y-%m-%d %H:%M:%S') + '"')

					# remove working file
					os.remove(filename)

					# keep tally of media migrated
					#print media_migration_record
					media_map = open(media_map_file, "a") 
					media_map.write(','.join(media_migration_record) + '\n')
					media_map.close()
					migrated_media_count = migrated_media_count + 1
					print "INF: Migrated medium '" + source_medium.id + "' to '" + migrated_medium['id'] + "'."
					
					# debug
					#debug_medium 	= sink_wordpress.call(posts.GetPost(migrated_medium['id']))
					#pp.pprint(vars(debug_medium))
					#debug_medium 	= sink_wordpress.call(posts.GetMediaItem(migrated_medium['id']))
					#pp.pprint(vars(debug_medium))
				else:
					print "INF: Media '" + source_medium.id + "' must be loaded manually."

			else:
				print "INF: Media '" + source_medium.id + "' was not migrated again."

			
			loops = loops + 1
		
		# get ready for next while loop
		offset = offset + increment		

	# print out how many media migrated and return number
	print "INF: Migrated " +  str(migrated_media_count) + " media files."
	return migrated_media_count

# post-fix to attach images to correct posts
def postfix_parent_images():

#                 or \
 #                locate(substring_index(image.guid, '/', -1), post.post_content)) \

	print "INF: Attaching images to parent posts..."
	sql = "select distinct image.id, post.id \
		from  \
		 wp_posts image \
		 join wp_posts post on ( post.post_content regexp concat('[[:<:]]', image.id, '[[:>:]]') \
                 or post.post_content regexp concat('[[:<:]]', substring_index(image.guid, '/', -1), '[[:>:]]') )\
		where  \
		 image.post_type = 'attachment' \
		 and image.post_parent = 0 \
		 and (post.post_type = 'post' or post.post_type = 'page') \
		 order by post.post_date desc"
	while True :
		try:
			output = mysql_sql(sink_wordpress_db, sql)
		except:
			db_check_connection(sink_wordpress_db, mysql_user, mysql_password, mysql_server, mysql_database)
			continue
		break
	#print "DBG: output = " + str(output)

	if len(output) > 0:
		for row in output:
			#print "DBG: row = " + str(row)
			sql = "update wp_posts set post_parent = " + str(row[1]) + " where id = " + str(row[0])
			#print "DBG: sql = " + sql
			while True :
				try:
					output = mysql_sql(sink_wordpress_db, sql)
				except:
					db_check_connection(sink_wordpress_db, mysql_user, mysql_password, mysql_server, mysql_database)
					continue
				break

	print "INF: Attached images to parent posts"
	return True

######## MIGRATE COMMENTS ########
# 'wp media regenerate --yes' has to be run on server commandline after media is migrated
def migrate_comments(source_post_id, sink_post_id):

	while True :
		try:
			source_comments = source_wordpress.call(comments.GetComments({'post_id': source_post_id, 'status': 'approve'}))
		except:
			check_connection(source_wordpress, source_url, source_user, source_password)
			continue
		break

	migrated_comment_count = 0

	if len(source_comments) > 0 :
		#comment_map = {}

		# load all comments for the current post
		for source_comment in source_comments:

			#print "DBG: source_comment = "
			#pp.pprint(vars(source_comment))
			#comment_parents = []
			# ... except pingbacks (TODO?)
			#if source_domain not in source_comment.author_url:

			# fix new comment 
			source_comment.post 			= sink_post_id # prob not necessary
			source_comment.post_title		= ''

			# source wordpress.com doesn't offer comment parents
			#source_comment_parent			= source_comment.parent
			#source_comment.parent			= '0'

			# add new comment
			while True :
				try:
					sink_comment_id				= sink_wordpress.call(comments.NewComment(sink_post_id, source_comment))
				except:
					check_connection(sink_wordpress, sink_url, sink_user, sink_password)
					continue
				break

			# correct new comment (because comments.NewComment buggers it up)
			while True :
				try:
					corrected_sink_comment 			= sink_wordpress.call(comments.GetComment(sink_comment_id))
				except:
					check_connection(sink_wordpress, sink_url, sink_user, sink_password)
					continue
				break

			corrected_sink_comment.author 		= source_comment.author
			corrected_sink_comment.author_email 	= source_comment.author_email
			corrected_sink_comment.author_ip 	= source_comment.author_ip
			corrected_sink_comment.date_created 	= source_comment.date_created

			# fix to use sink rather than source domain
			corrected_sink_comment.author_url = re.sub('/(?:www)?\.?' + source_domain + '/', '/www.' + sink_domain + '/', source_comment.author_url)
			corrected_sink_comment.content = re.sub('/(?:www)?\.?' + source_domain + '/', '/www.' + sink_domain + '/', source_comment.content)
			
			#print "DBG: sink_comment (post-correction) = "
			#pp.pprint(vars(corrected_sink_comment))
			while True :
				try:
					comment_tf = sink_wordpress.call(comments.EditComment(sink_comment_id, corrected_sink_comment))
				except:
					check_connection(sink_wordpress, sink_url, sink_user, sink_password)
					continue
				break

			migrated_comment_count = migrated_comment_count + 1
								
			# if xmlrpc doesnt support backdating or specified users - use mysql instead				
			# fix comment author and date via mysql
			#sql = "update wp_comments \
			#	 set comment_author 	= " + source_comment.author + \
			#	 "comment_author_email 	= " + source_comment.author_email + \
			#	 "comment_author_ip 	= " + source_comment.author_ip + \
			#	# "comment_date 		= " + source_comment.date_created + \
			#	"where comment_id 	= " + sink_comment.id + \
			#	 "and comment_post_id 	= " + migrated_post_id
			#print "DBG: sql = " + sql
			#sql_output = mysql_sql(sql)
			#print "DBG: sql_output = " + sql_output

			# map old comment ID to new comment ID (in prep for parent fix)
			#comment_map[source_comment.id] = sink_comment_id
			# append to list of comment parents
			#if source_comment_parent != '0' :
			#	comment_parents.append([sink_comment_id, source_comment_parent])

		# fix comment parents, if any, once ALL comments for this post have been entered
		#pp.pprint(vars(comment_map))
		#print comment_map
		#if len(comment_parents) > 0 :
		#	for comment_parent in comment_parents :
		#		corrected_sink_comment 		= sink_wordpress.call(comments.GetComment(comment_parent[0]))
		#		corrected_sink_comment.parent 	= comment_map[comment_parent[1]]

		#		print "DBG: sink_comment (post-parent-correction) = "
		#		pp.pprint(vars(corrected_sink_comment))
		#		sink_wordpress = check_connection(sink_wordpress, sink_url, sink_user, sink_password)
		#		comment_tf = sink_wordpress.call(comments.EditComment(comment_parent[0], corrected_sink_comment))

		if migrated_comment_count > 0:
			print "INF: Added " + str(migrated_comment_count) + " comments to post '" + sink_post_id + "'."

	return len(source_comments)

# post-fix to set comments to correct author
def postfix_comment_author():
	
	print "INF: Correcting comment authors..."
	sql = "update wp_comments set user_id = 0 where comment_author_url not like '%whitleypump.net%' and user_id != 0"
	while True :
		try:
			output = mysql_sql(sink_wordpress_db, sql)
		except:
			db_check_connection(sink_wordpress_db, mysql_user, mysql_password, mysql_server, mysql_database)
			continue
		break
	print "INF: Comment authors corrected"
	return True

##### MIGRATE IMAGE REFERENCES IN POSTS AND PAGES ######
# Example 1:
#[caption id="attachment_36664" align="aligncenter" width="676"]<a href="https://whitleypump.wordpress.com/?attachment_id=36664" target="_blank" rel="noopener"><img class="wp-image-36664 size-large" src="https://whitleypump.files.wordpress.com/2019/06/2019-06-22-17.53.34.jpg" alt="" width="676" height="505" /></a> 'After the Rain' by Calina Lefter[/caption]
# to
#[caption id="attachment_28000" align="aligncenter" width="1101"]<a href="http://www.whitleypump.net/?attachment_id=28000" target="_blank" rel="noopener noreferrer"><img class="wp-image-28000 size-full" src="http://www.whitleypump.net/wp-content/uploads/2019/06/2019-06-22-17.53.34.jpg" alt="" width="1101" height="822" /></a> 'After the Rain' - Calina Lefter[/caption]
# Example 2:
# [gallery type="rectangular" ids="36659,36662,36663,36660" orderby="rand"]
# to
# [gallery type="rectangular" ids="28001,28002,.. ,.. " orderby="rand"]
# code example from fix_post:
#fixed_content = re.sub(\
#	'<a href="(' + domain_name + '(?:(?!attachment_id).)*)">[\\b\s]*<img class="(.*?(\d+).*?)"[\\b\s]*src="(.*?)"(.*?)[\\b\s]*\/>[\\b\s]*<\/a>', \
#	'<a href="' + domain_name + '?attachment_id=\\3" target="_blank" rel="noopener"><img class="\\2" src="\\4" \\5 /></a>', \
#	fixed_content)

def image_ref_migrate(string):

	print "INF: migrating image references..."

	# log original string
	original_string = string

	# load up image reference translations from media map file
	migrated_image_id = {}
	migrated_image_url = {}
	with open(media_map_file) as media_map:  
	   for count, line in enumerate(media_map):
		#print "posts_map: " + line
		migrated_image_id[line.split(',')[0].replace('"', '').strip()] = line.split(',')[2].replace('"', '').strip()
		migrated_image_url[line.split(',')[1].replace('"', '').strip()] = line.split(',')[3].replace('"', '').strip()

	# ids
	for id in migrated_image_id.keys():
	
		#print "DBG: migrating image id '" + id + "' to '" + migrated_image_id[id] + "'."
		# 1. galleries
		# note '\\2 ' (with space) is mandatory because migrated_image_id[id] is a numeral
		string = re.sub('\[gallery\s+(.*?)ids=(.*?)\\b' + id + '\\b(.*?)\s+', \
				'[gallery \\1ids=\\2 ' + migrated_image_id[id] + '\\3 ', \
				string)
		# 2. id refs in url captions
		string = re.sub('\[caption\s+(.*?)id="attachment_' + id + '"', \
				'[caption \\1id="attachment_' + migrated_image_id[id] + '"', \
				string)
		# 3. id refs in url (attachment_id=X) attachment hrefs
		string = re.sub('<a href=".*?' + source_domain + '/\?attachment_id=' + id + '"\s+.*?>\s*<img\s+', \
				'<a href="https://www.' + sink_domain + '/?attachment_id=' + migrated_image_id[id] + '" target="_blank"><img ', \
				string)
		# 4. id refs in img classes
		string = re.sub('class="(.*?)wp-image-' + id + '\\b', \
				'class="\\1wp-image-' + migrated_image_id[id] + ' ', \
				string)

	# urls
	for url in migrated_image_url.keys():
	
		#print "DBG: migrating image url '" + url + "' to '" + migrated_image_url[url] + "'."
		# 5. url refs in img refs
		string = re.sub('src="' + url + '"', \
				'src="' + migrated_image_url[url] + '" ', \
				string)

	# 6. id/url refs in url (old version) attachment hrefs
	string = re.sub('<a href=".*?' + source_domain + '.*?"\s+.*?>\s*<img\s+class="(.*?(\d+).*?)"\s+', \
			'<a href="https://www.' + sink_domain + '/?attachment_id=\\2" target="_blank"><img class="\\1" ', \
			string)

	return string

# translates refs to old Wordpress to new Wordpress
# only need mapping if sink url is not calculable
def url_ref_migrate(string):

	print "INF: migrating URL references..."

	# load up post references
	#migrated_url = {}
	#with open(posts_map_file) as posts_map_translate:  
	#   for count, line in enumerate(posts_map_translate):
	#	#print "posts_map: " + line
	#	migrated_url[line.split(',')[1].replace('"', '').strip()] = line.split(',')[3].replace('"', '').strip()

	# references to specific posts and pages
	#for url in migrated_url.keys():
	#	string = re.sub(url,	migrated_url[url],	string)

	# any other reference (and hope for the best!)
	string = re.sub('/(?:www)?\.?' + source_domain + '/', 	'/www.' + sink_domain + '/',	string)

	return string


######## MIGRATE POSTS AND PAGES ########
def migrate_posts(post_id):
	
	max_loops = 10000

	#migrated_posts = posts_workfile_handler.readlines()
	#if len(migrated_posts) > 0 :
	#	print "The " + str(len(migrated_posts)) + " posts already migrated will not be migrated again."
	#posts_workfile_handler.close()

	migrated_posts = []
	with open(posts_map_file) as posts_map:  
	   for count, line in enumerate(posts_map):
	       migrated_posts.append(line.split(',')[0].strip('"'))

	# cycle through each post type to migrate
	if post_id is None:
		post_types = ['page', 'post']
		#post_types = ['page']
		#post_types = ['post']
	else:
		post_types = ['x']

	loops = 0
	migrated_post_count = 0
	for post_type in post_types:

		# get a list of all published source posts
		#offset = len(migrated_posts) # gets confusing with post/page
		offset = 0


		while True:
			
			if post_id is None:
				print "INF: extracting next " + str(increment) + " " + post_type +"s from source library starting at item " + str(offset) + "..."
				# keep trying until connection made
				while True :
					try:
						source_posts = source_wordpress.call(posts.GetPosts({'post_type': post_type, 'post_status': 'publish', 'orderby': 'date', 'order': 'ASC', 'number': increment, 'offset': offset}))
					except:
						check_connection(source_wordpress, source_url, source_user, source_password)
						continue
					break
			else:
				# debug only - pick one post to load
				source_posts = []
				source_posts.append(source_wordpress.call(posts.GetPost(post_id)))
				max_loops = 1 # force next loop fail after this loop

			# if no more posts returned (or debug limit reached), then stop
			if len(source_posts) == 0 or loops >= max_loops :
				break

			# for each post in the source list...
			for source_post in source_posts:

				# unmunged source post
				#pp.pprint(vars(source_post))

				# vars to hold working data
				migration_record = []
				page_record = []

				# if we have no record the post has already been migrated...
				if source_post.id not in migrated_posts:

					print "INF: migrating " + source_post.post_type + "# '" + source_post.id + "'..."

					# keep tally of work done
					migration_record.append('"' + source_post.id + '"')
					migration_record.append('"' + source_post.link + '"')

					# start assembling migrated post
					migrated_post 			= WordPressPost()
					migrated_post.post_status 	= 'publish'
					migrated_post.ping_status 	= 'open'
					migrated_post.post_format 	= 'standard'
					migrated_post.date 		= source_post.date
					migrated_post.date_modified 	= source_post.date_modified
					migrated_post.comment_status 	= 'open'
					migrated_post.post_type 	= source_post.post_type
					migrated_post.title 		= basic_cleanup(source_post.title)
					migrated_post.slug 		= re.sub('\s+', '-', migrated_post.title.lower().strip())

					# translate author
					#print "user '" + source_post.user + "' -> '" + user_migrate[source_post.user] + "'."
					migrated_post.user = user_migrate[source_post.user]

					# clean up content
					migrated_post.content 		= major_cleanup(source_post.content)

					# identify and replace internal image urls and IDs
					migrated_post.content 		= image_ref_migrate(migrated_post.content)

					# identify and replace internal refs to old website
					migrated_post.content 		= url_ref_migrate(migrated_post.content)

					# transfer post categories and tags
					if source_post.post_type != 'page':

						post_tags = []
						post_categories = []

						for source_post_term in source_post.terms:
							#pp.pprint(vars(source_post_term))
							# list tags attached to post
							if source_post_term.taxonomy == 'post_tag':
								post_tags.append(source_post_term.name)
							# list categories attached to post
							if source_post_term.taxonomy == 'category':
								post_categories.append(source_post_term.name)

						# append tag
						if len(post_tags) > 0 :
							migrated_post.terms_names = {'post_tag': post_tags}

						# append categories
						for sink_category in sink_categories:

							# categorise using source categories
							for post_category in post_categories:
								if post_category.lower() == sink_category.name.lower():
									migrated_post.terms.append(sink_category)

							# categorise post using regexp search - prob not a good idea on old posts
							#if re.search('\\b' + re.sub('\s', '\s+', re.sub('[Ss]?$', 's?', sink_category.name)) + '\\b', migrated_post.title + ' ' + migrated_post.content, flags=re.IGNORECASE | re.MULTILINE ) != None:
							#	migrated_post.terms.append(sink_category)

					# post to sink site
					while True :
						try:
							migrated_post_id = sink_wordpress.call(posts.NewPost(migrated_post))
						except:
							check_connection(sink_wordpress, sink_url, sink_user, sink_password)
							continue
						break

					# get link to new post (can probably be calculated, actually)
					#while True :
					#	try:
					#		migrated_post_link = sink_wordpress.call(posts.GetPost(migrated_post_id)).link
					#	except:
					#		check_connection(sink_wordpress, sink_url, sink_user, sink_password)
					#		continue
					#	break	
			
					# keep tally of work done
					#if len(migrated_post_link) > 0 :
					migrated_post_link = re.sub('/(?:www)?\.?' + source_domain + '/', '/www.' + sink_domain + '/', source_post.link)

					migration_record.append('"' + migrated_post_id + '"')
					migration_record.append('"' + migrated_post_link + '"')

					# additional pages fields
					if source_post.post_type == 'page':
						#migrated_post.template	= source_post.template
						#migrated_post.order	= source_post.order
						migrated_post.user = sink_me.id
						# cant do parent page here, as said page may not yet exist
						if source_post.parent_id != '0' :
							page_record.append('"' + source_post.id + '"')
							page_record.append('"' + source_post.parent_id + '"')
							page_record.append('"' + migrated_post_id + '"')
					
					# migrate comments
					migrate_comments(source_post.id, migrated_post_id)

					# turn off comments for old posts
					if source_post.date <= (datetime.today() - timedelta(days=int(365))) :
						migrated_post.comment_status 	= 'closed'
						while True :
							try:
								sink_wordpress.call(posts.EditPost(migrated_post_id, migrated_post))
							except:
								check_connection(sink_wordpress, sink_url, sink_user, sink_password)
								continue
							break	
						
					# keep tally of posts migrated
					posts_map = open(posts_map_file, "a") # running list of migrated posts (for script restart)
					posts_map.write(','.join(migration_record) + '\n')
					posts_map.close()

					if len(page_record) > 0 :
						pages_map = open(pages_map_file, "a") # running list pages parents
						pages_map.write(','.join(page_record) + '\n')  
						pages_map.close()
					
					migrated_post_count = migrated_post_count + 1					
					print "INF: Migrated " + source_post.post_type + " #" + source_post.id + " to #" + migrated_post_id + "."

				else:
					print "INF: Post '" + source_post.id + "' was not migrated again."

				loops = loops + 1

			# get ready for next while loop
			offset = offset + increment	

	print "INF: Migrated " +  str(migrated_post_count) + " pages and posts."
	return migrated_post_count

# post-fix for pages with parents (cant do this at same time as above as parent may not have been already loaded)
def postfix_page_parent():
	file_exists = True # edit to False to skip mapping page parentage
	for csvfile in [posts_map_file, pages_map_file ]:
		if not os.path.isfile(csvfile):
			file_exists = False

	if file_exists :
		print "INF: Mapping page parentage..."
		num_post_maps = 0
		# 1 - get a list mapping old post/page ids to new ones
		migrated_post_parent = {}
		with open(posts_map_file) as posts_map :  
		   for count, line in enumerate(posts_map):
			#print "posts_map: " + line
			migrated_post_parent[line.split(',')[0].replace('"', '').strip()] = line.split(',')[2].replace('"', '').strip()
			num_post_maps = num_post_maps + 1

		# 2 - go through pages with parents and use #1 to map old -> new
		if num_post_maps > 0 :
			with open(pages_map_file) as pages_map :  
			   for count, line in enumerate(pages_map) :
				#print "pages_map: " + line
				source_post_id 		= line.split(',')[0].replace('"', '').strip()
				source_post_parent_id 	= line.split(',')[1].replace('"', '').strip()
				migrated_post_id 	= line.split(',')[2].replace('"', '').strip()
				#print "source_post_id: " + source_post_id
				#print "source_post_parent_id: " + source_post_parent_id
				#print "migrated_post_id: " + migrated_post_id

				while True :
					try:
						migrated_post = sink_wordpress.call(posts.GetPost(migrated_post_id))
					except:
						check_connection(sink_wordpress, sink_url, sink_user, sink_password)
						continue
					break	

				if migrated_post.parent_id != migrated_post_parent[source_post_parent_id]:
					migrated_post.parent_id = migrated_post_parent[source_post_parent_id]
					while True :
						try:
							sink_wordpress.call(posts.EditPost(migrated_post.id, migrated_post))
						except:
							check_connection(sink_wordpress, sink_url, sink_user, sink_password)
							continue
						break	
		print "INF: Page parentage mapped."
	return True


##### INITIALISE ######
print "INF: Connecting..."
source_wordpress 	= connect_wordpress(source_url, source_user, source_password)
sink_wordpress 		= connect_wordpress(sink_url,   sink_user,   sink_password)

# db connection only required for dodgy post-fixes not supported by XML RPC API
sink_wordpress_db = connect_db(mysql_user, mysql_password, mysql_server, mysql_database)
print "INF: Connected!"

# set up working folders
for folder in [data_folder, media_folder]:
	if not os.path.isdir(folder):
		os.makedirs(folder)

# create migration files if not exist
for csvfile in [posts_map_file, pages_map_file, media_map_file]:
	if not os.path.isfile(csvfile):
		open(csvfile, "w").close()

##### GET REF DATA #####

print "INF: Getting reference data..."
# get profile of connected users
source_me = source_wordpress.call(users.GetProfile())
sink_me = sink_wordpress.call(users.GetProfile())

# get list of users on both systems
source_users = source_wordpress.call(users.GetAuthors())
sink_users = sink_wordpress.call(users.GetUsers())

# get list of categories on both system
source_categories = source_wordpress.call(taxonomies.GetTerms('category'))
sink_categories = sink_wordpress.call(taxonomies.GetTerms('category'))

# generate user translation map (author IDs in sink are not the same as source)
user_migrate = {}
for source_user in source_users:
	#pp.pprint(vars(source_user))

	# check sink list to see if user already added, and add it to translation map
	found = False
	if len(sink_users) > 0:
		for sink_user in sink_users:
			if source_user.user_login == sink_user.username:
				user_migrate[source_user.id] = sink_user.id
				found = True
				# print "Mapped user '" + source_user.id + "' to '" + sink_user.id + "'."
	# assume default user
	if not found:
		user_migrate[source_user.id] = sink_me.id
print "INF: Reference data retrieved"

# call to migrate media
#migrate_media(None)

# call to migrate posts
migrate_posts(None)

# postfixes
#postfix_page_parent()
postfix_comment_author()
postfix_parent_images()



