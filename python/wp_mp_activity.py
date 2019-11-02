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
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.command import Command
from selenium.webdriver import FirefoxOptions
ff_opts = FirefoxOptions()
#ff_opts.add_argument("-headless") # can be hardcoded here or set via getopts

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
start_date = default_startdate.strftime('%Y-%m-%d')
end_date = None
visible=1

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "c:s:e:h", ["constituency=", "startdate=", "enddate=", "headless"])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

for o, a in opts:
	if o in ("-c", "--constituency"):
		constituency = a.strip().title()	
	if o in ("-s", "--startdate"):
		start_date = a
	if o in ("-e", "--enddate"):
		end_date = a
	if o in ("-h", "--headless"):
		ff_opts.add_argument("-headless")
		visible=0

# clean up start_date
#print ('default_startdate=' + default_startdate.strftime('%Y-%m-%d') )
#print ('start_date=' + start_date)
#start_date = re.sub('[\x93\x94]', '"', start_date)
start_date = re.sub(ur'[\u201c\u201d]', '"', start_date)
start_date = start_date.replace('\\','')
#print start_date
#print json.loads(start_date)[constituency]

# check for required parms
if constituency is None:
	#print('ERR: Specify constituency')
	sys.exit(1)

# calculate start date
startDate=default_startdate
if start_date is not None:
	try:
		startDate=datetime.strptime(start_date, '%Y-%m-%d')
	except:
		try:
			# might be a JSON string from huginn credentials, which is the last day processed, so start from next day
			startDate=(datetime.strptime(json.loads(start_date)[constituency], '%Y-%m-%d') + timedelta(days=1))
		except: 
			startDate=default_startdate

# calculate end date (max 7 days because timeouts occur if longer)
default_enddate=(startDate + timedelta(days=7))
if default_enddate > datetime.now():
	default_enddate = datetime.now()
endDate=default_enddate
if end_date is not None:
	try:
		endDate=datetime.strptime(end_date, '%Y-%m-%d')
	except:
		endDate=default_enddate

#print json.loads(start_date.replace('\\"','"'))[constituency]
#print startDate
#print endDate
#sys.exit(0)

# start virtual display
# (note that size=(800, 600) results in "portal.find_element_by_xpath("//input[@value='Go' and @type='submit']").click()" doing nothing on ubuntu 16, but not fedora
#display=Display(visible=0, size=(1600, 1200)).start()
display=Display(visible=visible, size=(1600, 1200)).start() 

# 1. get MP name
portal=webdriver.Firefox(firefox_options=ff_opts)

# configure wait
wait = WebDriverWait(portal, 10);

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

# portal.get_screenshot_as_file('img.png') # useful for debugging headless installation
MP_url=portal.current_url
MP_id=MP_url.split('/')[-1]
html=BeautifulSoup(portal.page_source, 'html.parser')

try:
	MP_party=html.find("div", {"id" : "commons-party"}).string.strip()
	MP_name=re.sub(r' MP$', '', html.find("div", {"id" : "commons-biography-header"}).h1.string.strip().title(), flags=re.IGNORECASE)
	MP_email=html.find("p", {"data-generic-id" : "email-address"}).a.string.strip()
except:
	print('ERR: Unable to obtain MP details from ', MP_url)
	sys.exit(1)

#print MP_name
#print MP_email
#print MP_url
#print MP_id
#print MP_party

# 2.1 get MP activities
MP_parliamentary_activities=parliament_url + 'biographies/commons/' + MP_name.replace(' ', '-').lower() + '/' + MP_id + '/parliamentary-activities'
MP_spoken_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&startDate=' + startDate.strftime('%Y-%m-%d') + '&endDate=' + endDate.strftime('%Y-%m-%d') + '&type=Spoken&outputType=List'
#MP_written_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&type=Written'
#MP_corrections_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&type=Corrections'
MP_voting_url=hansard_url + 'search/MemberContributions?memberId=' + MP_id +  '&startDate=' + startDate.strftime('%Y-%m-%d') + '&endDate=' + endDate.strftime('%Y-%m-%d') + '&type=Divisions'
MP_qanda_url=hansard_url + 'business/publications/written-questions-answers-statements/written-questions-answers//?page=1&max=100&questiontype=AllQuestions&house=commons&member=' + MP_id

# 2.2 work out EDM URL
MP_EDM_url=None
try:
	portal.get(MP_parliamentary_activities)
except:
	#print('ERR: Unable to access "' + MP_parliamentary_activities + '"')
	sys.exit(1)

soup=BeautifulSoup(portal.page_source, 'html.parser')
try:
	MP_EDM_url=soup.find("a", {"id" : "ctlEarlyDayMotions_hypAllEDMsForMember"})['href']
except:
	MP_EDM_url=None
if MP_EDM_url != None:
	MP_EDM_url=parliament_url +  MP_EDM_url

# 3.1 spoken contributions
MP_spoken_contribs=None
MP_spoken_contrib_objs=[]
debate_portal=None
previous_debate=None

# debug code
#MP_spoken_url = None

# loop over each page
while MP_spoken_url is not None:

	# next page marker
	next=None

	# open MP contribution page
	try:
		portal.get(MP_spoken_url)
	except:
		#print('ERR: Unable to access "' + MP_spoken_url + '"')
		sys.exit(1)

	# close modal popup, if there is one
	#<button type="button" class="close" data-dismiss="modal" aria-hidden="true">x</button>
	popup=None
	try:
		popup=portal.find_element_by_xpath("//button[@class='close']")
	except:
		popup=None
	if popup is not None:
		#time.sleep(1)
		portal.execute_script("window.scrollTo(0, document.body.scrollHeight);")
		popup.click()

	# wait until results loaded
	# wait_element = wait.until(EC.text_to_be_present_in_element((By.CLASS_NAME, 'pagination-total'), 'Showing results'))
	try:
		wait_element = wait.until(EC.text_to_be_present_in_element((By.XPATH, '//p[@class="pagination-total"]'), 'Showing results') )
	except:
		wait_element = wait.until(EC.text_to_be_present_in_element((By.XPATH, '//div[@class="results-heading no-results"]/h2'), 'No results') )	

	# parse page
	soup=BeautifulSoup(portal.page_source, 'html.parser')

	# extract list of contribitions
	try:
		MP_spoken_contribs=soup.find('div', {"class" :'results-list row'}).find_all('div', {"class" :'col-sm-12 result-outer'})
	except:
		#print('ERR: Unable to find MP spoken contributions')
		#sys.exit(1)
		MP_spoken_contribs=[]

	# wind through list of contributions on page
	for MP_spoken_contrib in MP_spoken_contribs:

		# initialise object
		MP_spoken_contrib_obj={}
		MP_spoken_contrib_obj['detailed_contrib_text'] = None

		# get html
		MP_spoken_contrib_soup=BeautifulSoup(str(MP_spoken_contrib), 'html.parser')
		#print ('MP_spoken_contrib_soup=' + MP_spoken_contrib_soup.prettify() )

		# assemble spoken contrib obj
		if MP_spoken_contrib_soup.find("a") is not None:

			MP_spoken_contrib_obj['spoken_contrib_url']=hansard_url + MP_spoken_contrib_soup.a['href']
			MP_spoken_contrib_obj['spoken_contribution_id']=MP_spoken_contrib_obj['spoken_contrib_url'].split('#')[1]
			MP_spoken_contrib_obj['debate_url']=MP_spoken_contrib_obj['spoken_contrib_url'].split('#')[0]
			MP_spoken_contrib_obj['debate_title']=re.sub('[^\040-\176]', '', MP_spoken_contrib_soup.find("div", {"class" : "title single-line"}).span.string.strip())
			#MP_spoken_contrib_obj['debate_location']=MP_spoken_contrib_soup.find("div", {"class" : "information"}).string.strip()
			MP_spoken_contrib_obj['debate_date']=datetime.strptime( MP_spoken_contrib_soup.find("div", {"class" : "information"}).span.string.strip(), '%d %B %Y') #4 July 2017

			# debug
			#print "MP_spoken_contrib_obj['spoken_contrib_url']=" + MP_spoken_contrib_obj['spoken_contrib_url']
			#print "MP_spoken_contrib_obj['spoken_contribution_id']=" + MP_spoken_contrib_obj['spoken_contribution_id']
			#print "MP_spoken_contrib_obj['debate_url']=" + MP_spoken_contrib_obj['debate_url']
			#print "MP_spoken_contrib_obj['debate_title']=" + MP_spoken_contrib_obj['debate_title']
			#print "MP_spoken_contrib_obj['debate_date']=" + str(MP_spoken_contrib_obj['debate_date'])

			# get debate page when list rolls over to new debate
			if previous_debate is None or previous_debate != MP_spoken_contrib_obj['debate_url']:

				# close old debate html page (if any)
				if debate_portal is not None and get_status(debate_portal):
					debate_portal.close()

				# open new debate html page
				debate_portal=webdriver.Firefox(firefox_options=ff_opts)

				# get debate html
				try:
					debate_portal.get(MP_spoken_contrib_obj['debate_url'])
				except:
					#print('ERR: Unable to access "' + MP_spoken_contrib_obj['debate_url'] + '"')
					sys.exit(1)
				debate_soup=BeautifulSoup(debate_portal.page_source, 'html.parser')
	
			# extract MP's contribution detailed text
			try:
				MP_spoken_contrib_details=debate_soup.find("div", {"id" : MP_spoken_contrib_obj['spoken_contribution_id']}).find("div", {"class" : "inner"})
			except:
				MP_spoken_contrib_details=None

			if MP_spoken_contrib_details is not None:
				# extract contribution position in page (for later sorting)
				MP_spoken_contrib_obj['contrib_index']=debate_portal.page_source.find(MP_spoken_contrib_obj['spoken_contribution_id'])

				# note that not all <p> in target page contain text (some are empty, some are Hansard comments <em>...</em> 
				for MP_spoken_contrib_detail in MP_spoken_contrib_details.find_all("p"):
					#print "XX" + str(MP_spoken_contrib_detail) + "XX"
					if MP_spoken_contrib_detail.get_text() is not None and \
						len(MP_spoken_contrib_detail.get_text().strip()) > 0 and \
						re.match('^<p.*?><em>.*?<\/em><\/p>$', str(MP_spoken_contrib_detail)) == None:

						# replace bad spaces
						text=MP_spoken_contrib_detail.get_text().replace(unichr(160), " ").strip()
						#print "text=" + text

						# nonstandard quotes (" in string output can be problematic in JSON)
			 			text = re.sub('[\x93\x94]', "'", text)
						text = re.sub(ur'[\u201c\u201d]', "'", text)
						text = re.sub('[\x91\x92]', "'", text)	
						text = re.sub(ur'[\u2018\u2019\u201b]', "'", text)

						# malformed sentence ends
						text = re.sub('([^0-9]+)\.([^0-9]+)', '\\1. \\2', text)

						# strip (some) html (get_text() already does this)
						#text = re.sub('(<!--.*?-->|<[^>]*>)', ' ', text)

						# strip (some) nonprinting characters
						text = re.sub('[^\040-\176]', ' ', text)

						if MP_spoken_contrib_obj['detailed_contrib_text'] is None:
							MP_spoken_contrib_obj['detailed_contrib_text']=text
						else:
							MP_spoken_contrib_obj['detailed_contrib_text']=MP_spoken_contrib_obj['detailed_contrib_text'] + " " + text

			# prepare for next loop
			previous_debate=MP_spoken_contrib_obj['debate_url']

			# add MP_voting_contrib to array
			MP_spoken_contrib_objs.append(MP_spoken_contrib_obj)

			#debug
			#print "MP_spoken_contrib_obj=" + str(MP_spoken_contrib_obj)

	# check if there is another page, and loop again if there is
	MP_spoken_url=None
	try:
		next=portal.find_element_by_xpath("//li[@class='next']")
	except:
		next=None
	if next is not None:
		try:
			MP_spoken_url=hansard_url + soup.find('li', {"class" :'next'}).a['href']
		except:
			MP_spoken_url=None

# close debate portal, if any
if debate_portal is not None and get_status(debate_portal):
	debate_portal.close()
	
# 3.2 voting contributions
MP_voting_contribs=None
MP_voting_contrib_objs=[]

# debug code
#MP_voting_url = None

# loop over each page
while MP_voting_url is not None:

	# next page marker
	next=None

	# open MP contribution page
	try:
		portal.get(MP_voting_url)
	except:
		#print('ERR: Unable to access "' + MP_voting_url + '"')
		sys.exit(1)

	# close modal popup, if there is one
	#<button type="button" class="close" data-dismiss="modal" aria-hidden="true">x</button>
	popup=None
	try:
		popup=portal.find_element_by_xpath("//button[@class='close']")
	except:
		popup=None
	if popup is not None:
		portal.execute_script("window.scrollTo(0, document.body.scrollHeight);")
		popup.click()

	# wait until results loaded
	try:
		wait_element = wait.until(EC.text_to_be_present_in_element((By.XPATH, '//p[@class="pagination-total"]'), 'Showing results') )
	except:
		wait_element = wait.until(EC.text_to_be_present_in_element((By.XPATH, '//div[@class="results-heading no-results"]/h2'), 'No results') )	

	soup=BeautifulSoup(portal.page_source, 'html.parser')

	# extract list of contribitions
	try:
		MP_voting_contribs=soup.find('div', {"class" :'results-list row'}).find_all('div', {"class" :'col-sm-6 result-outer'})
	except:
		#print('ERR: Unable to find MP voting contributions')
		#sys.exit(1)
		MP_voting_contribs=[]

	# wind through list of contributions on page
	for MP_voting_contrib in MP_voting_contribs:

		# initialise object
		MP_voting_contrib_obj={}

		# extract html
		MP_voting_contrib_soup=BeautifulSoup(str(MP_voting_contrib), 'html.parser')
		#print ('MP_voting_contrib_soup=' + MP_voting_contrib_soup.prettify() )

		# assemble voting contrib object
		if MP_voting_contrib_soup.find("a") is not None:

			MP_voting_contrib_obj['voting_contrib_url']=hansard_url + MP_voting_contrib_soup.a['href']
			MP_voting_contrib_obj['bill_or_debate_url']=MP_voting_contrib_obj['voting_contrib_url'].split('#')[0]
			MP_voting_contrib_obj['bill_or_debate_title']=re.sub('[^\040-\176]', '',  MP_voting_contrib_soup.find("div", {"class" : "title single-line"}).span.string.strip())
			#MP_voting_contrib_obj['bill_or_debate_division']=MP_voting_contrib_soup.find("div", {"class" : "information"}).div.string.strip().lower()
			MP_voting_contrib_obj['bill_or_debate_division']=MP_voting_contrib_soup.find(string=re.compile("division", re.IGNORECASE)).lower()
			MP_voting_contrib_obj['bill_or_debate_MP_vote']="<em>" + MP_voting_contrib_soup.find("div", {"class" : "vote-result vote-result-commons"}).string.strip() + "</em>"

			# 2 date formats in use
			try:
				MP_voting_contrib_obj['bill_or_debate_date']=datetime.strptime( MP_voting_contrib_soup.find("div", {"class" : "sitting-date"}).string.strip(), '%d %B %Y %I.%M %p') #4 July 2017 9.35pm
			except:
				MP_voting_contrib_obj['bill_or_debate_date']=datetime.strptime( MP_voting_contrib_soup.find("div", {"class" : "sitting-date"}).string.strip(), '%d %B %Y') #4 July 2017

			MP_voting_contrib_obj['bill_or_debate_vote_counts']=''
			for vote_count in MP_voting_contrib_soup.find("div", {"class" : "counts"}).findAll("strong"):
				if len(MP_voting_contrib_obj['bill_or_debate_vote_counts']) == 0:
					MP_voting_contrib_obj['bill_or_debate_vote_counts']=re.sub("((ay|no)e?s?)", "<em>\\1</em>", vote_count.string.strip().lower().replace(':', ''), flags=re.IGNORECASE)
				else:
					MP_voting_contrib_obj['bill_or_debate_vote_counts']=MP_voting_contrib_obj['bill_or_debate_vote_counts'] + ' and ' + re.sub("((ay|no)e?s?)", "<em>\\1</em>", vote_count.string.strip().lower().replace(':', ''), flags=re.IGNORECASE)

			# add MP_voting_contrib to array
			MP_voting_contrib_objs.append(MP_voting_contrib_obj)

			#debug
			#print "MP_voting_contrib_obj=" + str(MP_voting_contrib_obj)

	# check if there is another page, and loop again if there is
	try:
		next=portal.find_element_by_xpath("//li[@class='next']")
	except:
		next=None
	if next is not None:
		MP_voting_url=hansard_url + soup.find('li', {"class" :'next'}).a['href']
	else:
		MP_voting_url=None


# 3.3 early day motions
# need to distinguish support, primary sponsor and sponsor?
MP_EDMs=None
MP_EDM_objs=[]

# open MP contribution page
try:
	portal.get(MP_EDM_url)
except:
	#print('ERR: Unable to access "' + MP_EDM_url + '"')
	MP_EDM_url=None

# debug code
#MP_EDM_url=None

while MP_EDM_url != None:

	# next page marker
	next=None

	soup=BeautifulSoup(portal.page_source, 'html.parser')

	# extract list of contribitions
	try:
		MP_EDMs=soup.find('table', {"id" :'topic-list'}).find('tbody').find_all('tr')
	except:
		#print('ERR: Unable to find MP EDMs')
		#sys.exit(1)
		MP_EDMs=[]

	# wind through list of contributions on page
	for MP_EDM in MP_EDMs:

		# initialise object
		MP_EDM_obj={}

		# extract html
		MP_EDM_soup=BeautifulSoup(str(MP_EDM), 'html.parser')
		#print ('MP_EDM_soup=' + MP_EDM_soup.prettify() )

		# assemble EDM object
		MP_EDM_obj['number']=MP_EDM_soup.find_all('td')[0].a.span.next_sibling
		MP_EDM_obj['url']=parliament_url +  MP_EDM_soup.find_all('td')[0].a['href']
		MP_EDM_obj['title']=MP_EDM_soup.find_all('td')[1].find('a').get_text().title()
		MP_EDM_obj['date_signed']=datetime.strptime( MP_EDM_soup.find_all('td')[2].get_text(), '%d.%m.%Y')
		MP_EDM_obj['signatures']=MP_EDM_soup.find_all('td')[3].get_text()

		# add MP_voting_contrib to array if new enough
		#pp.pprint(MP_EDM_obj['date_signed'])
		if MP_EDM_obj['date_signed'] >= startDate and MP_EDM_obj['date_signed'] <= endDate:
			MP_EDM_objs.append(MP_EDM_obj)

			# debug
			#pp.pprint(MP_EDM_obj)

	#next=portal.find_element_by_xpath("//li[@class='next']") #.find_element_by_xpath("//a[contains(text(), 'Next')]")
	#next.click()
	# check if there is another page, and loop again if there is
	try:
		next=portal.find_element_by_xpath("//li[@class='next']").find_element_by_xpath("//a[text()='Next']")
	except:
		break
	if next != None:
		next.click()
	else:
		break

# shut down browser
portal.close()
display.stop()

# variable to hold latest contribution date (for restarts)
since=startDate

# 4.1 sort spoken objects by date and assemble string
MP_spoken_contribs_text=""
MP_spoken_contrib_count_text= "not contributed to any speeches"
debate_count_text = ""
if len(MP_spoken_contrib_objs) > 0:

	MP_spoken_contrib_objs.sort(key=lambda x: (x['debate_date'], x['debate_title'], x['contrib_index']))
	debate_count = 0
	previous_debate=None
	MP_spoken_contribs_text=''

	for MP_spoken_contrib_obj in MP_spoken_contrib_objs:

		if MP_spoken_contrib_obj['detailed_contrib_text'] is not None and len(MP_spoken_contrib_obj['detailed_contrib_text']) > 0:

			# write new debate header and get debate page when list rolls over to new debate
			if previous_debate is None or previous_debate != MP_spoken_contrib_obj['debate_url']:
				debate_count = debate_count + 1
				if len(MP_spoken_contribs_text.strip()) == 0:
					MP_spoken_contribs_text="<h5>Speeches</h5>" + MP_name + " spoke on the <a href=" + MP_spoken_contrib_obj['debate_url'] + " target=_blank>" + MP_spoken_contrib_obj['debate_title'] + "</a> debate on " + MP_spoken_contrib_obj['debate_date'].strftime('%-d %B') + ": "
				else:
					MP_spoken_contribs_text=MP_spoken_contribs_text + "<br>" + MP_name + " spoke on the <a href=" + MP_spoken_contrib_obj['debate_url'] + " target=_blank>" + MP_spoken_contrib_obj['debate_title'] + "</a> debate on " + MP_spoken_contrib_obj['debate_date'].strftime('%-d %B') + ": "

			# debug
			#print "MP_spoken_contrib_obj['detailed_contrib_text']=" + MP_spoken_contrib_obj['detailed_contrib_text']

			# write out debate details re.sub('[^\040-\176]', '', MP_spoken_contrib_detail.get_text().strip())
			MP_spoken_contribs_text=MP_spoken_contribs_text + '<blockquote>' + re.sub(' +', ' ', MP_spoken_contrib_obj['detailed_contrib_text']).strip() + '</blockquote>'

			# keep track of latest date of all contributions
			if since==None or MP_spoken_contrib_obj['debate_date'] > since:
				since=MP_spoken_contrib_obj['debate_date']

			# prepare for next loop
			previous_debate=MP_spoken_contrib_obj['debate_url']

	if len(MP_spoken_contrib_objs) == 1:
		MP_spoken_contrib_count_text= "spoken once"
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
	elif  len(MP_spoken_contrib_objs) == 9:
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


# 4.2 sort voting objects by date and assemble string
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
	elif  len(MP_voting_contrib_objs) == 9:
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

# 4.2 sort EDM objects by date and assemble string
MP_EDM_text=""
MP_EDM_count_text="not supported any new early day motions"
if len(MP_EDM_objs) > 0:

	MP_EDM_objs.sort(key=lambda x: (x['date_signed'],x['number']))
	EDM_count = 0

	MP_EDM_text="<h5>Early day motions</h5>" + MP_name + " sponsored or supported these <a href=http://www.parliament.uk/edm target=_blank>early day motions</a>.<br><br><ol>"

	for MP_EDM_obj in MP_EDM_objs:
		EDM_count = EDM_count + 1
		MP_EDM_text=MP_EDM_text + "<li> <a href=" + MP_EDM_obj['url'] + " target=_blank>" + MP_EDM_obj['title'] + "</a> (" + MP_EDM_obj['signatures'] + " signatures)</li>"

	MP_EDM_text=MP_EDM_text + "</ol>"

	if  len(MP_EDM_objs) == 1:
		MP_EDM_count_text= "supported one early day motion"
	elif  len(MP_EDM_objs) == 2:
		MP_EDM_count_text= "supported two early day motions"
	elif  len(MP_EDM_objs) == 3:
		MP_EDM_count_text= "supported three early day motions"
	elif  len(MP_EDM_objs) == 4:
		MP_EDM_count_text= "supported four early day motions"
	elif  len(MP_EDM_objs) == 5:
		MP_EDM_count_text= "supported five early day motions"
	elif  len(MP_EDM_objs) == 6:
		MP_EDM_count_text= "supported six early day motions"
	elif  len(MP_EDM_objs) == 7:
		MP_EDM_count_text= "supported seven early day motions"
	elif  len(MP_EDM_objs) == 8:
		MP_EDM_count_text= "supported eight early day motions"
	elif  len(MP_EDM_objs) == 9:
		MP_EDM_count_text= "supported nine early day motions"
	else:
		MP_EDM_count_text= "supported " + str(len(MP_voting_contrib_objs)) + " early day motions"

# this cludge is intended to make sure the 'since' credential doesn't just crawl along a day at a time when there is no data to retrieve
if len(MP_spoken_contrib_objs) == 0 and len(MP_voting_contrib_objs) == 0 and len(MP_EDM_objs) == 0 and since < (datetime.now() - timedelta(days=4)):
	since = endDate

# 5 assemble final JSON string ready for Huginn de-stringifier
credential={}
credential[constituency]=since.strftime('%Y-%m-%d')	
output={}
output['credential']=	'mp_activity_since=' + json.dumps(credential)

if len(MP_spoken_contrib_objs) > 0 or len(MP_voting_contrib_objs) > 0 or len(MP_EDM_objs) > 0:

	header_image=''
	extra_links=''
	if constituency == 'Reading West':	
		output['wards']='Whitley, Minster'
		candidate_images=[14671,26583]
		extra_links='<li><a href=https://www.theyworkforyou.com/mp/24902/alok_sharma/reading_west target=_blank>' + MP_name + ' at TheyWorkForYou</a></li>' + \
				"<li><a href=http://www.aloksharma.co.uk/ target=_blank>" + MP_name + "'s website</a></li>"
	elif constituency == 'Reading East':	
		output['wards']='Katesgrove, Redlands, Church, Abbey, Park'
		candidate_images=[15006,14672,14535,14446,26584]
		extra_links='<li><a href=https://www.theyworkforyou.com/mp/25691/matt_rodda/reading_east target=_blank>' + MP_name + ' at TheyWorkForYou</a></li>' + \
				"<li><a href=http://www.mattrodda.net/ target=_blank>" + MP_name + "'s website</a></li>"
	else:
		output['wards']='unknown'
		candidate_images=[]

	if len(candidate_images) > 0:
		header_image='[gallery type="rectangular" size="full" ids="' + str(random.choice(candidate_images)) + '" orderby="rand"]<br>'

	if startDate == since :
		date_string=' on ' +  startDate.strftime('%-d %B')
	else:
		date_string=' from ' + startDate.strftime('%-d %B') + ' to ' + since.strftime('%-d %B')
	
	output['title']=	'Parliamentary activity of ' + constituency + ' MP ' + MP_name + date_string
	output['intro_para']=	header_image + constituency.title() + ' MP <a href=' + MP_url + ' target=_blank>' + MP_name + '</a> has ' + \
				MP_spoken_contrib_count_text + debate_count_text + ', ' + \
				MP_voting_contrib_count_text + bill_or_debate_count_text + ' and has ' + \
				MP_EDM_count_text + \
				date_string + '.'
	output['body_para']=	MP_spoken_contribs_text.strip() + \
				MP_voting_contribs_text.strip() + \
				MP_EDM_text.strip() + \
				'<br><p style=text-align:right><em>Sourced from <a href=http://www.parliament.uk target=_blank>www.parliament.uk</a></em></p>'
	output['link_list']=	'<li><a href=' + MP_url + ' target=_blank>' + MP_name + ' at parliament.uk</a></li><li><a href=https://whitleypump.wordpress.com/?s=' + re.sub(' +', '+', MP_name) + ' target=_blank>' + MP_name + ' on the <i>Whitley Pump</i></a></li>' + extra_links

# always write output (including mp_activity_since)
print (json.dumps(output))
