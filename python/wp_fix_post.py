#! /usr/bin/python

import getopt, sys, re, pprint, urlparse
import time as t
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, taxonomies, media

pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "x:u:p:i:", ["url=", "user=", "password=", "id="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

url = 'https://x.wordpress.com/xmlrpc.php'
user = None
password = None
post_id = None

for o, a in opts:
	if o in ("-x", "--url"):
		url = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a
	elif o in ("-i", "--id"):
		post_id = a

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

# get list of posts
subject_post = None
if post_id is not None:
	subject_post = wordpress.call(posts.GetPost(post_id))

if subject_post is not None:

	# calculate domain name
	domain_name=urlparse.urljoin(url, '/')

	# fix title
	fixed_title = subject_post.title

	# fix non-standard or duplicate spaces
	fixed_title = fixed_title.replace(unichr(160), " ")
	fixed_title = re.sub(' +', ' ', fixed_title)

	# fix non-standard quotes
	fixed_title = re.sub('[\x93\x94]', 			'"', fixed_title)
	fixed_title = re.sub(ur'[\u201c\u201d]', 		'"', fixed_title)
	fixed_title = re.sub('[\x91\x92]', 			"'", fixed_title)	
	fixed_title = re.sub(ur'[\u2018\u2019\u201b]', 		"'", fixed_title)

	# remove html
	fixed_title = re.sub('<.*?>', 				'', fixed_title)

	# convert '&' to 'and' (html entity shows up in FB/TW
	fixed_title = re.sub('&amp;', 				'and', fixed_title)

	#print subject_post.content

	# fix content for known errors
	fixed_content = subject_post.content

	# replace non-standard quotes with "\x22" or 'x27'
	fixed_content = re.sub('[\x93\x94]', 				'"', fixed_content)
	fixed_content = re.sub(ur'[\u201c\u201d]', 			'"', fixed_content)
	fixed_content = re.sub('[\x91\x92]', 				"'", fixed_content)	
	fixed_content = re.sub(ur'[\u2018\u2019\u201b]', 		"'", fixed_content)

	# replace doubled-up quotes unless preceded with '='
	fixed_content = re.sub('(?<!=)([\'\"])\\1', 			'\\1', fixed_content)

	# remove redundant div tags
	#fixed_content = re.sub('</?div.*?>', '', fixed_content)
	fixed_content = re.sub('<div>(.*?)</div>', 			'\\1', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<div\s+id=".*?"\s*>(.*?)</div>', 	'\\1', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<div\s+lang=".*?"\s*>(.*?)</div>', 	'\\1', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<div\s+class=".*?"\s*>(.*?)</div>', 	'\\1', fixed_content, flags=re.DOTALL)

	# remove redundant span tags
	#fixed_content = re.sub('</?span.*?>', '', fixed_content)
	fixed_content = re.sub('<span>(.*?)</span>', 			'\\1', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<span\s+id=".*?"\s*>(.*?)</span>', 	'\\1', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<span\s+lang=".*?"\s*>(.*?)</span>', 	'\\1', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<span\s+class=".*?"\s*>(.*?)</span>', 	'\\1', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<span\s+style=".*?"\s*>(.*?)</span>', 	'\\1', fixed_content, flags=re.DOTALL)

        # remove redundant p tags
        fixed_content = re.sub('<p>(.*?)</p>', 				'\\1<br>', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<p\s+id=".*?"\s*>(.*?)</p>', 		'\\1<br>', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<p\s+lang=".*?"\s*>(.*?)</p>', 		'\\1<br>', fixed_content, flags=re.DOTALL)
	fixed_content = re.sub('<p\s+class=".*?"\s*>(.*?)</p>', 	'\\1<br>', fixed_content, flags=re.DOTALL)

        # remove redundant <br id> tags
        fixed_content = re.sub('<br\s+id=".*?"\s*/>\s+', 			'\n', fixed_content)

	# Make sure sentence starts are capitalised

	# make ellipses standard
	fixed_content = re.sub('(\.+\s+)?\.{2,}(\s*\.+)?', '... ', fixed_content)

	# Make sure sentence ends are spaced
	#fixed_content = re.sub('(\w)+\s*\.\s*(\w)+(?!\.)', '\\1 XXX \\2', fixed_content) # this also buggers up URLs #-ve lookback assertn: (?<!\.)

	# remove duplicated punctuation
	fixed_content = re.sub('(&amp;){2,}', 				'\\1', fixed_content) # &&
	fixed_content = re.sub('([\(\)]){2,}', 				'\\1', fixed_content) # (( )) () )( -> first one
	fixed_content = re.sub('([!?,:;$]){2,}', 			'\\1', fixed_content) # !?,:;%$- followed by any one of that set again
	fixed_content = re.sub('[!?,:;]\.', 				'.',   fixed_content) # !. ?. ,. :. ;. -. -> .
	fixed_content = re.sub('\.([!?,:;])', 				'\\1', fixed_content) # as above, but reversed -> first one

	# make sure "xxx ," doesnt happen
	fixed_content = re.sub('\\b(\w+)\s+,\s?', 			'\\1, ', fixed_content)

	# ensure all links open in new page
	fixed_content = re.sub(\
		'<(a(?=\s+|>)(?!(?:[^>=]|=([\'\"])(?:(?!\\2).)*\\2)*?\s+target=)[^>]*)>(?!\s*<\s*img\\b)', \
		'<\\1 target="_blank">', \
		fixed_content)

	# ensure all internal links (aka bookmarks with href="#abc") *dont* open in new page
	fixed_content = re.sub('<a(?=\s+|>)\s+(href=([\'\"])#(?:(?!\\2).)*\\2)(.*?)>','<a \\1>', fixed_content)

	# ensure all pics open correct page 
	# fix pics with no link
	fixed_content = re.sub(\
		'<img class="(.*?(\d+).*?)"[\\b\s]*src="(.*?)"(.*?)[\\b\s]*\/>', \
		'<a href="' + domain_name + '?attachment_id=\\2" target="_blank" rel="noopener"><img class="\\1" src="\\3" \\4 /></a>', \
		fixed_content)

	# fixed duplicated hrefs (where post has mix of linked and unlinked pics)
	fixed_content = re.sub(\
		'(<a href=".*?" .*?>)(<a href=".*?" .*?>)(<img .*? \/>)(<\/a><\/a>)', \
		'\\2\\3</a>', \
		fixed_content)

	# fix pics with 'custom link'
	fixed_content = re.sub(\
		'<a href="(' + domain_name + '(?:(?!attachment_id).)*)">[\\b\s]*<img class="(.*?(\d+).*?)"[\\b\s]*src="(.*?)"(.*?)[\\b\s]*\/>[\\b\s]*<\/a>', \
		'<a href="' + domain_name + '?attachment_id=\\3" target="_blank" rel="noopener"><img class="\\2" src="\\4" \\5 /></a>', \
		fixed_content)

	# fix common spelling errors TODO esc URLs
	#fixed_content = re.sub('\\b([Cc])llr\\b', '\\1ouncillor', fixed_content)
	#fixed_content = re.sub('\\b(t)hr\\b', 		'\\1he', 	fixed_content, flags=re.IGNORECASE)
	#fixed_content = re.sub('\\b(d)ont\\b', 		'\\1on\'t', 	fixed_content, flags=re.IGNORECASE)
	#fixed_content = re.sub('\\b(d)idnt\\b', 	'\\1idn\'t', 	fixed_content, flags=re.IGNORECASE)
	#fixed_content = re.sub('\\b(c)ouldnt\\b', 	'\\1ouldn\'t', 	fixed_content, flags=re.IGNORECASE)
	#fixed_content = re.sub('\\buk(\'s)?\\b', 	'UK\\1', 	fixed_content, flags=re.IGNORECASE)
	#fixed_content = re.sub('\\bmp(\'s)?\\b', 	'MP\\1', 	fixed_content, flags=re.IGNORECASE)
	#fixed_content = re.sub('\\beurope(.*?)\\b',	'Europe\\1', 	fixed_content, flags=re.IGNORECASE)

	# remove double lines
	fixed_content = re.sub('(\n\s*){2,}', r'\n\n', 			fixed_content, flags=re.MULTILINE)

	# remove double spaces
	#fixed_content = re.sub(ur'\u00a0', ' ', fixed_content) # inserts bollox char
	fixed_content = fixed_content.replace(unichr(160), " ")
	fixed_content = re.sub(' +', ' ', fixed_content) # \s also collapses newlines

	# remove initial blank line (this can remove *all* blank lines)
	fixed_content = re.sub('\A(?: |&nbsp;|\n)*(.*)', '\\1', fixed_content, flags=re.MULTILINE)

	# correctly form initial byline (if any)
	fixed_content = re.sub('\A(?:<em>)?\s*(By\\b.*?)[\.\s]*(?:<\/em>)?\n', '<em>\\1.</em>\n', fixed_content, flags=(re.IGNORECASE | re.MULTILINE))	
	
	# remove terminal blank line
	fixed_content = re.sub('(.*)(?: |&nbsp;|\n)*\Z', '\\1', fixed_content, flags=re.MULTILINE)

	# add more line after first para, if one not already included
	if not re.search('<!--more-->', fixed_content, re.IGNORECASE):
		#fixed_content = re.sub('(\w)+\n*', r'\\1\n\n<!--more-->\n', fixed_content, count=1, flags=re.MULTILINE)
		fixed_content = re.sub('^(<a[^\n]+</a>\n+[^\n]+)\n*', '\\1\n\n<!--more-->\n', fixed_content, count=1, flags=re.MULTILINE)

	# make sure more line is correctly spaced
	fixed_content = re.sub('(?:(<br ?/? ?>|\n))*<(?:!-*)?more(?:-*)?>(?:(<br ?/? ?>|\n))*', r'\n\n<!--more-->', fixed_content, flags=re.MULTILINE)

	# Headify Links header
	fixed_content = re.sub('<hr ?\/? ?>\n+Links ?\n+', '<hr />\n<h5>Links</h5>\n', fixed_content, flags=re.MULTILINE)

	# autolinkify known words TODO esc already linked
	# use datamap.hyperlinks view for source data	
		
	# categorize if not already categorised
	if len(subject_post.terms) == 1 and subject_post.terms[0].name == 'Uncategorized':
		categories = wordpress.call(taxonomies.GetTerms('category'))
		for category in categories:
			#pp.pprint(vars(category))
			if category.name != 'Uncategorized':
				category_search_name = re.sub('\s*ward$', '', category.name)
				#print category.name
				#print category_search_name
				if re.search('\\b' + category_search_name + '\'?s?\\b', fixed_content, re.IGNORECASE):
					subject_post.terms.append(category)

	# remove 'uncategorized' if otherwise categorized
	if len(subject_post.terms) > 1:
		count_term = 0
		for term in subject_post.terms:
			#pp.pprint(vars(term))
			if term.name != 'Uncategorized':
				count_term = count_term + 1
			else:
				break
		if count_term < len(subject_post.terms):
			subject_post.terms.pop(count_term)

	updated = 0
	# update post with fixed title if it looks big enough
	if fixed_title != subject_post.title and len(fixed_title) > ((len(subject_post.title) * 5)/10) and len(fixed_title) < ((len(subject_post.title) * 12)/10):
		subject_post.title = fixed_title
		updated = 1

	# update post with fixes if it looks big enough (ie, hasnt been bolloxed completely)
	if fixed_content != subject_post.content and len(fixed_content) > ((len(subject_post.content) * 5)/10) and len(fixed_content) < ((len(subject_post.content) * 12)/10):
		subject_post.content = fixed_content
		updated = 1

	#subject_post.excerpt = subject_post.title + ' by ' + output_event['author']

	# post changes if an updated has been made
	if updated == 1 :
		edit_post = wordpress.call(posts.EditPost(post_id, subject_post))
                #print fixed_content

