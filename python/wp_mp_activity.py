#! /usr/bin/python
import urllib2, sys, getopt, random, time, re, pprint, httplib, socket, json
from datetime import datetime, timedelta
from operator import itemgetter, attrgetter#, methodcaller
 
# webdriver modules
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.command import Command
 
# virtual display
from pyvirtualdisplay import Display

# web page extraction and parsing
from bs4 import BeautifulSoup
import lxml.html

# configure pretty printer
pp = pprint.PrettyPrinter(indent=1,width=80,depth=3)

def get_status(driver):
    try:
        driver.execute(Command.STATUS)
        return True
    except (socket.error, httplib.CannotSendRequest):
        return False

# init
parliament_url='http://www.parliament.uk/'
hansard_url='https://hansard.parliament.uk/'
mps_url=parliament_url + 'mps-lords-and-offices/mps/'
constituency=None
default_startdate=(datetime.now() - timedelta(days=7))

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "c:s:", ["constituency=", "startdate="])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

for o, a in opts:
	if o in ("-c", "--constituency"):
		constituency = a.strip().title()	
	if o in ("-s", "--startdate"):
		start_date = a	

# check for required parms
if constituency is None:
	#print('ERR: Specify constituency')
	sys.exit(1)

# calculate dates
endDate=datetime.now()
if start_date is None:
	startDate=default_startdate
else:
	try:
		startDate=datetime.strptime(start_date, '%Y-%m-%d')
	except:
		try:
			# might be a JSON string from huginn credentials, which is the last day processed, so start from next day
			startDate=(datetime.strptime(json.loads(start_date.replace('\\"','"'))[constituency], '%Y-%m-%d') + timedelta(days=1))
		except: 
			startDate=default_startdate

#print json.loads(start_date.replace('\\"','"'))[constituency]
#print startDate
#sys.exit(0)

# start virtual display
display=Display(visible=0, size=(800, 600)).start()

# 1. get MP name
portal=webdriver.Firefox()
try:
	portal.get(mps_url)
except:
	#print('ERR: Unable to access ' + mps_url )
	sys.exit(1)

try:
	portal.find_element_by_xpath("//input[@class='searchbox' and @type='text']").send_keys(constituency)
except:
	#print('ERR: Unable to find searchbox')
	sys.exit(1)

try:
	portal.find_element_by_xpath("//input[@value='Go' and @type='submit']").click()
except:
	#print('ERR: Unable to search for "' + constituency + '"')
	sys.exit(1)

MP_url=portal.current_url
MP_id=MP_url.split('/')[-1]
html=BeautifulSoup(portal.page_source, 'html.parser')

try:
	MP_party=html.find("div", {"id" : "commons-party"}).string.strip()
	MP_name=re.sub(r' MP$', '', html.find("div", {"id" : "commons-biography-header"}).h1.string.strip().title(), flags=re.IGNORECASE)
	MP_email=html.find("p", {"data-generic-id" : "email-address"}).a.string.strip()
except:
	#print('ERR: Unable to find MP details')
	sys.exit(1)

#print MP_name
#print MP_email
#print MP_url
#print MP_id
#print MP_party

# 2. get MP activities
MP_spoken_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&startDate=' + startDate.strftime('%Y-%m-%d') + '&endDate=' + endDate.strftime('%Y-%m-%d') + '&type=Spoken&outputType=List'
#MP_written_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&type=Written'
#MP_corrections_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&type=Corrections'
MP_voting_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&startDate=' + startDate.strftime('%Y-%m-%d') + '&endDate=' + endDate.strftime('%Y-%m-%d') + '&type=Divisions'
#MP_qanda_url='http://www.parliament.uk/business/publications/written-questions-answers-statements/written-questions-answers//?page=1&max=100&questiontype=AllQuestions&house=commons&member=' + MP_id

#print MP_spoken_url
#sys.exit(2)

# 2.1 spoken contributions

MP_spoken_contribs=None
MP_spoken_contrib_objs=[]
debate_portal=None
previous_debate=None

while MP_spoken_url is not None:

	# next page marker
	next=None

	# open MP contribution page
	try:
		portal.get(MP_spoken_url)
	except:
		#print('ERR: Unable to access "' + MP_spoken_url + '"')
		sys.exit(1)

	html=BeautifulSoup(portal.page_source, 'html.parser')

	# extract list of contribitions
	try:
		MP_spoken_contribs=html.find('div', {"class" :'results-list row'}).find_all('div', {"class" :'col-sm-12 result-outer'})
	except:
		#print('ERR: Unable to find MP spoken contributions')
		sys.exit(1)

	# wind through list of contributions on page
	for MP_spoken_contrib in MP_spoken_contribs:

		# initialise object
		MP_spoken_contrib_obj={}
		MP_spoken_contrib_obj['detailed_contrib_text'] = None

		# get html
		MP_spoken_contrib_html=BeautifulSoup(str(MP_spoken_contrib), 'html.parser')

		# assemble spoken contrib obj
		MP_spoken_contrib_obj['spoken_contrib_url']=hansard_url + MP_spoken_contrib_html.a['href']
		MP_spoken_contrib_obj['spoken_contribution_id']=MP_spoken_contrib_obj['spoken_contrib_url'].split('#')[1]
		MP_spoken_contrib_obj['debate_url']=MP_spoken_contrib_obj['spoken_contrib_url'].split('#')[0]
		MP_spoken_contrib_obj['debate_title']=re.sub('[^\040-\176]', '', MP_spoken_contrib_html.find("div", {"class" : "title single-line"}).span.string.strip())
		#MP_spoken_contrib_obj['debate_location']=MP_spoken_contrib_html.find("div", {"class" : "information"}).string.strip()
		MP_spoken_contrib_obj['debate_date']=datetime.strptime( MP_spoken_contrib_html.find("div", {"class" : "information"}).span.string.strip(), '%d %B %Y') #4 July 2017

		# get debate page when list rolls over to new debate
		if previous_debate is None or previous_debate != MP_spoken_contrib_obj['debate_url']:

			# close old debate html page (if any)
			if debate_portal is not None and get_status(debate_portal):
				debate_portal.close()

			# open new debate html page
			debate_portal=webdriver.Firefox()

			# get debate html
			try:
				debate_portal.get(MP_spoken_contrib_obj['debate_url'])
			except:
				#print('ERR: Unable to access "' + MP_spoken_contrib_obj['debate_url'] + '"')
				sys.exit(1)
			debate_html=BeautifulSoup(debate_portal.page_source, 'html.parser')
	
		# extract MP's contribution detailed text
		MP_spoken_contrib_details=debate_html.find("li", {"id" : MP_spoken_contrib_obj['spoken_contribution_id']}).find("div", {"class" : "inner"})

		# note that not all <p> in target page contain text
		for MP_spoken_contrib_detail in MP_spoken_contrib_details.find_all("p"):
			if MP_spoken_contrib_detail.get_text() is not None and len(MP_spoken_contrib_detail.get_text().strip()) > 0:
				if MP_spoken_contrib_obj['detailed_contrib_text'] is None:
					MP_spoken_contrib_obj['detailed_contrib_text']=re.sub('[^\040-\176]', '', MP_spoken_contrib_detail.get_text().strip())
				else:
					MP_spoken_contrib_obj['detailed_contrib_text']=MP_spoken_contrib_obj['detailed_contrib_text'] + re.sub('[^\040-\176]', '', MP_spoken_contrib_detail.get_text().strip())


		# prepare for next loop
		previous_debate=MP_spoken_contrib_obj['debate_url']

		# add MP_voting_contrib to array
		MP_spoken_contrib_objs.append(MP_spoken_contrib_obj)

	# check if there is another page, and loop again if there is
	try:
		next=portal.find_element_by_xpath("//li[@class='next']")
	except:
		next=None
	if next is not None:
		MP_spoken_url=hansard_url + html.find('li', {"class" :'next'}).a['href']
	else:
		MP_spoken_url=None

# close debate portal, if any
if debate_portal is not None and get_status(debate_portal):
	debate_portal.close()
	
# 2.2 voting contributions
MP_voting_contribs=None
MP_voting_contrib_objs=[]

while MP_voting_url is not None:

	# next page marker
	next=None

	# open MP contribution page
	try:
		portal.get(MP_voting_url)
	except:
		#print('ERR: Unable to access "' + MP_voting_url + '"')
		sys.exit(1)

	html=BeautifulSoup(portal.page_source, 'html.parser')

	# extract list of contribitions
	try:
		MP_voting_contribs=html.find('div', {"class" :'results-list row'}).find_all('div', {"class" :'col-sm-6 result-outer'})
	except:
		#print('ERR: Unable to find MP voting contributions')
		sys.exit(1)

	# wind through list of contributions on page
	for MP_voting_contrib in MP_voting_contribs:

		# initialise object
		MP_voting_contrib_obj={}

		# extract html
		MP_voting_contrib_html=BeautifulSoup(str(MP_voting_contrib), 'html.parser')

		# assemble voting contrib object
		MP_voting_contrib_obj['voting_contrib_url']=hansard_url + MP_voting_contrib_html.a['href']
		MP_voting_contrib_obj['bill_or_debate_url']=MP_voting_contrib_obj['voting_contrib_url'].split('#')[0]
		MP_voting_contrib_obj['bill_or_debate_title']=re.sub('[^\040-\176]', '',  MP_voting_contrib_html.find("div", {"class" : "title single-line"}).span.string.strip())
		MP_voting_contrib_obj['bill_or_debate_division']=MP_voting_contrib_html.find("div", {"class" : "information hidden-xs"}).div.string.strip().lower()
		MP_voting_contrib_obj['bill_or_debate_MP_vote']="'" + MP_voting_contrib_html.find("div", {"class" : "col-sm-2 commons-vote-label "}).span.string.strip() + "'"

		# 2 date formats in use
		try:
			MP_voting_contrib_obj['bill_or_debate_date']=datetime.strptime( MP_voting_contrib_html.find("div", {"class" : "sitting-date"}).string.strip(), '%d %B %Y %I.%M %p') #4 July 2017 9.35pm
		except:
			MP_voting_contrib_obj['bill_or_debate_date']=datetime.strptime( MP_voting_contrib_html.find("div", {"class" : "sitting-date"}).string.strip(), '%d %B %Y') #4 July 2017

		MP_voting_contrib_obj['bill_or_debate_vote_counts']=''
		for vote_count in MP_voting_contrib_html.find("div", {"class" : "counts"}).findAll("strong"):
			if len(MP_voting_contrib_obj['bill_or_debate_vote_counts']) == 0:
				MP_voting_contrib_obj['bill_or_debate_vote_counts']=re.sub("((ay|no)e?s?)", "'\\1'", vote_count.string.strip().lower().replace(':', ''), flags=re.IGNORECASE)
			else:
				MP_voting_contrib_obj['bill_or_debate_vote_counts']=MP_voting_contrib_obj['bill_or_debate_vote_counts'] + ' and ' + re.sub("((ay|no)e?s?)", "'\\1'", vote_count.string.strip().lower().replace(':', ''), flags=re.IGNORECASE)

		# add MP_voting_contrib to array
		MP_voting_contrib_objs.append(MP_voting_contrib_obj)

	# check if there is another page, and loop again if there is
	try:
		next=portal.find_element_by_xpath("//li[@class='next']")
	except:
		next=None
	if next is not None:
		MP_voting_url=hansard_url + html.find('li', {"class" :'next'}).a['href']
	else:
		MP_voting_url=None


# shut down browser
portal.close()
display.stop()

# variable to hold latest contribution date (for restarts)
since=None

# sort spoken objects by date and assemble string
MP_spoken_contribs_text=""
MP_spoken_contrib_count_text= "not contributed to any speeches"
debate_count_text = ""
if len(MP_spoken_contrib_objs) > 0:

	MP_spoken_contrib_objs.sort(key=lambda x: x['debate_date'])
	debate_count = 0
	previous_debate=None
	MP_spoken_contribs_text=''

	for MP_spoken_contrib_obj in MP_spoken_contrib_objs:

		# write new debate header and get debate page when list rolls over to new debate
		if previous_debate is None or previous_debate != MP_spoken_contrib_obj['debate_url']:
			debate_count = debate_count + 1
			if len(MP_spoken_contribs_text.strip()) == 0:
				MP_spoken_contribs_text="<h5>Speeches</h5>" + MP_name + " spoke on the <a href=" + MP_spoken_contrib_obj['debate_url'] + " target=_blank>" + MP_spoken_contrib_obj['debate_title'] + "</a> debate on " + MP_spoken_contrib_obj['debate_date'].strftime('%-d %B') + ": "
			else:
				MP_spoken_contribs_text=MP_spoken_contribs_text + "<br>" + MP_name + " spoke on the <a href=" + MP_spoken_contrib_obj['debate_url'] + " target=_blank>" + MP_spoken_contrib_obj['debate_title'] + "</a> debate on " + MP_spoken_contrib_obj['debate_date'].strftime('%-d %B') + ": "

		# write out debate details
		MP_spoken_contribs_text=MP_spoken_contribs_text + '<blockquote>' + MP_spoken_contrib_obj['detailed_contrib_text'] + '</blockquote>'

		# keep track of latest date of all contributions
		if since==None or MP_spoken_contrib_obj['debate_date'] > since:
			since=MP_spoken_contrib_obj['debate_date']

		# prepare for next loop
		previous_debate=MP_spoken_contrib_obj['debate_url']

	if len(MP_spoken_contrib_objs) == 1:
		MP_spoken_contrib_count_text= "spoke once"
	elif  len(MP_spoken_contrib_objs) == 2:
		MP_spoken_contrib_count_text= "spoken twice"
	elif  len(MP_spoken_contrib_objs) == 3:
		MP_spoken_contrib_count_text= "spoken three times"
	elif  len(MP_spoken_contrib_objs) == 4:
		MP_spoken_contrib_count_text= "spoken four times"
	elif  len(MP_spoken_contrib_objs) == 5:
		MP_spoken_contrib_count_text= "spoken five times"
	elif  len(MP_spoken_contrib_objs) == 6:
		MP_spoken_contrib_count_text= "spoken six times"
	elif  len(MP_spoken_contrib_objs) == 7:
		MP_spoken_contrib_count_text= "spoken seven times"
	elif  len(MP_spoken_contrib_objs) == 8:
		MP_spoken_contrib_count_text= "spoken eight times"
	elif  len(MP_spoken_contrib_objs) == 8:
		MP_spoken_contrib_count_text= "spoken nine times"
	else:
		MP_spoken_contrib_count_text= "spoken " + str(len(MP_spoken_contrib_objs)) + " times"

	if debate_count == 1:
		debate_count_text = " on one debate"
	elif debate_count == 2:
		debate_count_text = " on two debates"
	elif debate_count == 3:
		debate_count_text = " on three debates"
	elif debate_count == 4:
		debate_count_text = " on four debates"
	elif debate_count == 5:
		debate_count_text = " on five debates"
	elif debate_count == 6:
		debate_count_text = " on six debates"
	elif debate_count == 7:
		debate_count_text = " on seven debates"
	elif debate_count == 8:
		debate_count_text = " on eight debates"
	elif debate_count == 9:
		debate_count_text = " on nine debates"
	else:
		debate_count_text= " on " + str(debate_count) + " debates"


# sort voting objects by date and assemble string
MP_voting_contribs_text=""
MP_voting_contrib_count_text= "not voted in any debates"
bill_or_debate_count_text = ""
if len(MP_voting_contrib_objs) > 0:

	MP_voting_contrib_objs.sort(key=lambda x: x['bill_or_debate_date'])
	bill_or_debate_count = 0
	previous_bill_or_debate=None
	MP_voting_contribs_text=''

	for MP_voting_contrib_obj in MP_voting_contrib_objs:

		# write new debate header and get debate page when list rolls over to new debate
		if previous_bill_or_debate is None or previous_bill_or_debate != MP_voting_contrib_obj['bill_or_debate_url']:
			bill_or_debate_count = bill_or_debate_count + 1
			if len(MP_voting_contribs_text.strip()) == 0:
				MP_voting_contribs_text="<h5>Votes</h5> A vote can take place at any point in a debate (a 'division'). You need to review the context of each vote to understand what was being voted on.<br><br>" + \
				MP_name + " voted on the <a href='" + MP_voting_contrib_obj['bill_or_debate_url'] + "' target=_blank>" + \
				MP_voting_contrib_obj['bill_or_debate_title'] + "</a> debate on " + MP_voting_contrib_obj['bill_or_debate_date'].strftime('%-d %B') + ": <ol>"
			else:
				MP_voting_contribs_text=MP_voting_contribs_text + "</ol><br>" + MP_name + " voted on the <a href=" + \
				MP_voting_contrib_obj['bill_or_debate_url'] + " target=_blank>" + MP_voting_contrib_obj['bill_or_debate_title'] + \
				"</a> debate on " + MP_voting_contrib_obj['bill_or_debate_date'].strftime('%-d %B') + ": <ol>"

		MP_voting_contribs_text=MP_voting_contribs_text + '<li>' + MP_voting_contrib_obj['bill_or_debate_MP_vote'] + ' on <a href=' + \
		MP_voting_contrib_obj['voting_contrib_url'] + ' target=_blank>' +  MP_voting_contrib_obj['bill_or_debate_division'] + \
		'</a> (' + str(MP_voting_contrib_obj['bill_or_debate_vote_counts']) + ') </li>'


		# keep track of latest date of all contributions
		if since==None or MP_voting_contrib_obj['bill_or_debate_date'] > since:
			since=MP_voting_contrib_obj['bill_or_debate_date']

		# prepare for next loop
		previous_bill_or_debate=MP_voting_contrib_obj['bill_or_debate_url']

	# terminate bullet list of last list of divisions
	MP_voting_contribs_text=MP_voting_contribs_text + "</ol>"

	if  len(MP_voting_contrib_objs) == 1:
		MP_voting_contrib_count_text= "voted once"
	elif  len(MP_voting_contrib_objs) == 2:
		MP_voting_contrib_count_text= "voted twice"
	elif  len(MP_voting_contrib_objs) == 3:
		MP_voting_contrib_count_text= "voted three times"
	elif  len(MP_voting_contrib_objs) == 4:
		MP_voting_contrib_count_text= "voted four times"
	elif  len(MP_voting_contrib_objs) == 5:
		MP_voting_contrib_count_text= "voted five times"
	elif  len(MP_voting_contrib_objs) == 6:
		MP_voting_contrib_count_text= "voted six times"
	elif  len(MP_voting_contrib_objs) == 7:
		MP_voting_contrib_count_text= "voted seven times"
	elif  len(MP_voting_contrib_objs) == 8:
		MP_voting_contrib_count_text= "voted eight times"
	elif  len(MP_voting_contrib_objs) == 8:
		MP_voting_contrib_count_text= "voted nine times"
	else:
		MP_voting_contrib_count_text= "voted " + str(len(MP_voting_contrib_objs)) + " times"

	if bill_or_debate_count == 1:
		bill_or_debate_count_text = " on one debate"
	elif bill_or_debate_count == 2:
		bill_or_debate_count_text = " on two debates"
	elif bill_or_debate_count == 3:
		bill_or_debate_count_text = " on three debates"
	elif bill_or_debate_count == 4:
		bill_or_debate_count_text = " on four debates"
	elif bill_or_debate_count == 5:
		bill_or_debate_count_text = " on five debates"
	elif bill_or_debate_count == 6:
		bill_or_debate_count_text = " on six debates"
	elif bill_or_debate_count == 7:
		bill_or_debate_count_text = " on seven debates"
	elif bill_or_debate_count == 8:
		bill_or_debate_count_text = " on eight debates"
	elif bill_or_debate_count == 9:
		bill_or_debate_count_text = " on nine debates"
	else:
		bill_or_debate_count_text= " on " + str(bill_or_debate_count) + " debates"


# assemble final JSON string ready for Huginn de-stringifier
if len(MP_spoken_contrib_objs) > 0 or len(MP_voting_contrib_objs) > 0:

	credential={}
	credential[constituency]=since.strftime('%Y-%m-%d')	

	output={}
	output['title']='Parliamentary activity of ' + constituency + ' MP ' + MP_name + ' from ' + startDate.strftime('%-d %B') + ' to ' + since.strftime('%-d %B')
	output['intro_para']=constituency.title() + ' MP <a href=' + MP_url + ' target=_blank>' + MP_name + '</a> has ' + MP_spoken_contrib_count_text + debate_count_text + ' and has ' + MP_voting_contrib_count_text + bill_or_debate_count_text + ' between ' + startDate.strftime('%-d %B') + ' and ' + since.strftime('%-d %B') + '.'
	output['body_para']=MP_spoken_contribs_text.strip() + MP_voting_contribs_text.strip() + '<br><p style=text-align:right><em>Sourced from <a href=http://www.parliament.uk target=_blank>www.parliament.uk</a></em></p>'
	output['link_list']='<li><a href=' + MP_url + ' target=_blank>' + MP_name + '</a><li><a href=http://www.parliament.uk target=_blank>www.parliament.uk</a></li><li><a href=https://www.theyworkforyou.com target=_blank>TheyWorkForYou</a></li>'
	output['credential']='mp_activity_since=' + json.dumps(credential)

	print (json.dumps(output))
