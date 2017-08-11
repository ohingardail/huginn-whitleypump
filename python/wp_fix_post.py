#! /usr/bin/python

import getopt, sys, re, pprint
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

url = 'https://milmanroad.wordpress.com/xmlrpc.php'
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
	#print(err)
	sys.exit(1)

# get list of posts
subject_post = None
if post_id is not None:
	subject_post = wordpress.call(posts.GetPost(post_id))

if subject_post is not None:

	#print subject_post.content

	# fix content for known errors
	fixed_content = subject_post.content

	# replace non-standard quotes with "\x22" or 'x27'
	fixed_content = re.sub('[\x93\x94]', '"', fixed_content)
	fixed_content = re.sub(ur'[\u201c\u201d]', '"', fixed_content)
	fixed_content = re.sub('[\x91\x92]', "'", fixed_content)	
	fixed_content = re.sub(ur'[\u2018\u2019\u201b]', "'", fixed_content)

	# replace doubled-up quotes unless preceded with '='
	fixed_content = re.sub('(?<!=)([\'\"])\\1', '\\1', fixed_content)

	# remove div tags
	fixed_content = re.sub('</?div.*?>', '', fixed_content)

	# remove span tags
	fixed_content = re.sub('</?span.*?>', '', fixed_content)

        # remove p tags
        fixed_content = re.sub('</?p.*?>', '\n', fixed_content)

	# Make sure sentence starts are capitalised

	# make ellipses standard
	fixed_content = re.sub('\.{2,}', '... ', fixed_content)

	# Make sure sentence ends are spaced
	#fixed_content = re.sub('(\w)+\s*\.\s*(\w)+(?!\.)', '\\1 XXX \\2', fixed_content) # this also buggers up URLs #-ve lookback assertn: (?<!\.)

	# remove duplicated punctuation
	fixed_content = re.sub('(&amp;){2,}', '\\1', fixed_content) # &&
	fixed_content = re.sub('([\(\)]){2,}', '\\1', fixed_content) # (( )) () )( -> first one
	fixed_content = re.sub('([!?,:;%$]){2,}', '\\1', fixed_content) # !?,:;%$- followed by any one of that set again
	fixed_content = re.sub('[!?,:;]\.', '.', fixed_content) # !. ?. ,. :. ;. -. -> .
	fixed_content = re.sub('\.([!?,:;])', '\\1', fixed_content) # as above, but reversed -> first one

	# ensure all links open in new page
	fixed_content = re.sub('<(a(?=\s|>)(?!(?:[^>=]|=([\'\"])(?:(?!\\2).)*\\2)*?\starget=)[^>]*)>(?!\s*<\s*img\\b)','<\\1 target="_blank">', fixed_content)

	# ensure all pics open correct page 
	# may not be poss example https://whitleypump.wordpress.com/20170402_143212/ -> https://whitleypump.wordpress.com/?attachment_id=13263

	# fix common spelling errors TODO esc URLs
	#fixed_content = re.sub('\\b([Tt])hr\\b', '\\1he', fixed_content)
	#fixed_content = re.sub('\\b([Cc])llr\\b', '\\1ouncillor', fixed_content)
	#fixed_content = re.sub('\\b([DdWw])ont\\b', '\\1on\'t', fixed_content)
	#fixed_content = re.sub('\\b([Dd])idnt\\b', '\\1idn\'t', fixed_content)
	#fixed_content = re.sub('\\b([Cc])ouldnt\\b', '\\1ouldn\'t', fixed_content)

	# autolinkify known words TODO esc already linked
	
	# add more line after first para, if one not already included
	if not re.search('<!--more-->', fixed_content, re.IGNORECASE):
		#fixed_content = re.sub('(\w)+\n*', r'\\1\n\n<!--more-->\n', fixed_content, count=1, flags=re.MULTILINE)
		fixed_content = re.sub('^(<a[^\n]+</a>\n+[^\n]+)\n*', '\\1\n\n<!--more-->\n', fixed_content, count=1, flags=re.MULTILINE)

	# remove double lines
	fixed_content = re.sub('(\n\s*){2,}', r'\n\n', fixed_content, flags=re.MULTILINE)

	# make sure more line is correctly spaced
	fixed_content = re.sub('(?:(<br ?/? ?>|\n))*<(?:!-*)?more(?:-*)?>(?:(<br ?/? ?>|\n))*', r'\n\n<!--more-->', fixed_content, flags=re.MULTILINE)

	# Headify Links header
	fixed_content = re.sub('<hr ?\/? ?>\n+Links ?\n+', '<hr />\n<h5>Links</h5>\n', fixed_content, flags=re.MULTILINE)

	# remove double spaces
	#fixed_content = re.sub(ur'\u00a0', ' ', fixed_content) # inserts bollox char
	fixed_content = fixed_content.replace(unichr(160), " ")
	fixed_content = re.sub(' +', ' ', fixed_content) # \s also collapses newlines

	# remove initial blank line (this can remove *all* blank lines)
	fixed_content = re.sub('\A(?: |&nbsp;|\n)*(.*)', '\\1', fixed_content, flags=re.MULTILINE)
			
	# categorize if not already categorised
	if len(subject_post.terms) == 1 and subject_post.terms[0].name == 'Uncategorized':
		categories = wordpress.call(taxonomies.GetTerms('category'))
		for category in categories:
			#pp.pprint(vars(category))
			if category.name != 'Uncategorized':
				category_search_name = re.sub('\s*ward$', '', category.name)
				#print category.name
				#print category_search_name
				if re.search('\\b' + category_search_name + '\\b', fixed_content, re.IGNORECASE):
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

	# update post with fixes and new excerpt if it looks big enough (ie, hasnt been bolloxed completely)
	if fixed_content != subject_post.content and len(fixed_content) > ((len(subject_post.content) * 5)/10) and len(fixed_content) < ((len(subject_post.content) * 11)/10):
		subject_post.content = fixed_content
		#subject_post.excerpt = subject_post.title + ' by ' + output_event['author']
		edit_post = wordpress.call(posts.EditPost(post_id, subject_post))
                #print fixed_content

