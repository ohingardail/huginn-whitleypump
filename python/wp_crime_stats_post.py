#! /usr/bin/python
# Script to generate wordpress post and graph from police data (https://data.police.uk/)

# load required libraries
import getopt, sys, pprint, copy, re, random
from types import *
import requests 		# http://docs.python-requests.org/en/master/
import mysql.connector 		# https://dev.mysql.com/doc/connector-python/en
import json

# time and date stuff
from time import sleep
from datetime import datetime, timedelta
import calendar
from dateutil import relativedelta

# matplotlib libraries
import matplotlib
matplotlib.use('Agg') # uncomment to print to file
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors

# hard coded defaults
user = '' 	# mysql user
password = '' 	# mysql password
database = '' 	# mysql database
host = '' 	# mysql host
region = '' 	# Reading Borough Council'
options = ''		# specialised options debugging etc

# place to store plot files
plotfile_store = '/tmp/'
# default graph font
matplotlib.rc('font',family='DejaVu Sans')
#graphfont = {'fontname':'FreeSans'}

# always returns YYYY-MM-DD where DD is the last day of the month and MM is 01-12
def standardise_date(date_string):
	if date_string is None or len(date_string) == 0:
		return None
	# convert to date
	try:
		date_value = datetime.strptime(date_string, '%Y-%m-%d')
	except:
		print "ERR: unable to convert string '" + date_string + "' into a date"
		return None
	date_string = str(date_value.year) + '-' + str(date_value.month).rjust(2, '0') + '-' + str(calendar.monthrange(date_value.year, date_value.month)[1])
	return date_string

# always returns MONTH YYYY where MONTH = January-December
# used for human-readibility in graphs etc
def humanise_date(date_string):
	if date_string is None or len(date_string) == 0:
		return None
	# convert to date
	try:
		date_value = datetime.strptime(date_string, '%Y-%m-%d')
	except:
		print "ERR: unable to convert string '" + date_string + "' into a date"
		return None
	date_string = calendar.month_name[date_value.month] + ' ' +  str(date_value.year) 
	return date_string

# returns date <months> months ago from date_string; returned as string in %Y-%m-%d format
def months_ago(date_string, months):
	return datetime.strftime( datetime.strptime(date_string, '%Y-%m-%d') - relativedelta.relativedelta(months = months), '%Y-%m-%d')

# calls specified sql and returns result
# result is a LIST containing ONE BARE TUPLE which are the column names 
# and a LIST containing data tuples (ie rows)
# example : 
# HEADER>     [(u'category', u'a', u'b', u'c'), 
# DATA_START>  [
# ROW_1>        (u'violent crime', Decimal('124'), Decimal('220'), Decimal('253')), 
# ROW_2>        (u'anti social behaviour', Decimal('250'), Decimal('262'), Decimal('221'))
# DATA_END>    ]
# END>        ]
# print resultset(0) - column names (as one tuple)
# print resultset(1) - all data rows (as a list of tuples)
def mysql_sql(query):
	if query is None:
		print "ERR: mysql_sql : must specify query"
		return None
	# print "DBG: query = " + query
	resultset = []
	mysql_sql = db.cursor()
	try:
		mysql_sql.execute(query)
	except:
		print 'ERR: mysql_sql query "' + query + '" failed.'
		return None
	resultset.append(mysql_sql.column_names)
	resultset.append(mysql_sql.fetchall())
	# print resultset
	mysql_sql.close()
	if resultset is not None:
		return resultset
	return None

# convert region list to form used in SQL "'X','Y',Z'" & English "X, Y and Z"
def convert_list(data):
	sql_region = ""
	english_region = ""
	region_tot=len(region.split(','))
	region_count=0
	for r in region.split(','):
		r=r.title()
		region_count = region_count + 1
		if len(sql_region) == 0:
			sql_region="'" + r + "'"
		else:	
			sql_region=sql_region + ", '" + r + "'"
		if len(english_region) == 0:
			english_region=r
		else:	
			if region_count == region_tot and region_tot > 1:
				english_region=english_region + " and " + r
			else:
				english_region=english_region + ", " + r
	return [sql_region, english_region]

# converts mysql_sql output into HTML
def html_table(data):
	html_header = None
	for element in data[0]:
		if html_header is None:
			html_header = '<th>' + element + '</th>'
		else:
			html_header = html_header + '<th>' + element + '</th>'
	html_header = '<tr>' + html_header + '</tr>'
	html_body =  None
	for row in data[1]:
		html_row = None
		if row[0].lower() == 'total':
			td_start = '<th>'
			td_end = '</th>' 
		else:
			td_start = '<td>'
			td_end = '</td>' 
		for element in row:
			if html_row is None:
				html_row = td_start + str(element) + td_end
			else:
				html_row = html_row + td_start + str(element) + td_end
		if html_body is None:
			html_body = '<tr>' + html_row + '</tr>'
		else:
			html_body = html_body + '<tr>' + html_row + '</tr>'
	return '<table>'+ html_header + html_body + '</table>'

# calls specified mysql procedure
def mysql_procedure(procedure, params):
	if procedure is None:
		print "ERR: mysql_procedure : must specify procedure"
		return None
	mysql_procedure = db.cursor()
	try:
		out = mysql_procedure.callproc(procedure, params)
	except:
		print 'ERR: mysql_procedure failed.'
		return False
	db.commit()
	mysql_procedure.close()
	return True

# calls specified mysql function and returns result
def mysql_function(function, params):
	if function is None:
		print "ERR: mysql_function : must specify function"
		return None
	query = 'select '+ function + '('
	if len(params) == 0:
		query = query + ')'
	else:
		for param in params:
			if param is None:
				query = query + "null,"
			elif type(param) is StringType or type(param) is UnicodeType:	
				query = query + "'" + re.sub('[\"\']', '', str(param.encode("utf-8"))) + "',"
			else:
				query = query + str(param) + ","
		query = re.sub(',$', ')', query)
	# print "DBG: query = " + query
	mysql_function = db.cursor()
	try:
		mysql_function.execute(query)
	except:
		print 'ERR: mysql_function query "' + query + '" failed.'
		return None
	resultset = mysql_function.fetchone()
	# print resultset
	db.commit()
	mysql_function.close()
	if resultset is not None:
		return resultset[0]
	return None

# pivots data structure
# data = data structure provided by mysql_sql (qv)
# base_cols column(s) on the left, separated by commas
# pivot_col name of column to put across the top
# tally_rtn aggregation routine ('sum' or 'count', usually)
# tally_col name of column to aggregate
#def pivot (data, base_cols, pivot_col, tally_rtn, tally_col)
#	if data is None:
#		return None
#	if tally_rtn is None:
#		tally_rtn = "count"

# expects data as a list of tuples [(1,2,3),(4,5,6)], xvalues as tuples ('a','b','c') and legend (aka series names) as a tuple ('x','y','z')
def plot_barchart(data, xvalues, series, title, xlabel, ylabel):

	#print "data: " + str(data)
	#print "series: " + str(series)
	#print "xvalues: " + str(xvalues)

	# maxwidth and maxheight of plot
	#plot_width=10
	#plot_height=10
	
	# default title
	if title is None:
		title = "Barchart"

	if xlabel is None:
		xlabel = "Category?"

	if ylabel is None:
		ylabel = "Number?"

	if series is None:
		series = ('data')

	if xvalues is None:
		xvalues = range(len(data[0]))

	# calculate reasonable bar width
	bar_width = round( 1 / (len(series)+1.0) , 2)
	#print "bar_width:" + str(bar_width)
	#bar_width = 0.5
	#if bar_width < 0.2:
	#	bar_width = 0.2
	#if bar_width > 1:
	#	bar_width = 1

	# x-item range (#columns in table (ie #x values))
	x_items_index = range(len(xvalues))

	# start creating plot
	#fig, barplot = plt.subplots(figsize=(plot_width,plot_height))
	fig, barplot = plt.subplots()
	barplot.set_title(title)
	barplot.set_ylabel(ylabel)
	barplot.set_xlabel(xlabel)
	#barplot.set_xticks([ind + (bar_width * (len(data[0])/2) ) for ind in x_items_index])
	barplot.set_xticks([ind + (bar_width * len(series)/2 ) for ind in x_items_index])
	barplot.set_xticklabels(xvalues, rotation=90, fontsize='small')

	# work through data; each line assumed to be a 'series' with a 1:1 relationship with rows in 'legend'

	bar_series = []
	row_count = 0
	for row in data:
		#print [ind + (bar_width * (row_count) ) for ind in x_items_index]
		bar_series.append(barplot.bar([ind + (bar_width * (row_count) ) for ind in x_items_index], row, bar_width, color=cm.Set3(float(row_count) / len(series)), label=series[row_count], align='edge', linewidth=0))
		#print (str(row_count) + ', ' + str(len(series)) + ', ' + str(float(row_count) / len(series)) )
		row_count += 1

	# add labels to bars
	(y_bottom, y_top) = barplot.get_ylim()
	y_height = y_top - y_bottom
	for bar_serie in bar_series:
		for bar_rect in bar_serie:
			height = float(bar_rect.get_height())
			p_height = height / y_height
			if p_height > 0.9:
				label_position = height - (y_height * 0.1)
			else:
				label_position = height + (y_height * 0.01)
	       		barplot.text(bar_rect.get_x() + bar_rect.get_width()/1.5, label_position,'%d' % int(height), fontsize='small', ha='center', va='bottom', rotation=90)
			# print str(height) + ":" + str(label_position)

	# create legend (depends on 'label' when setting up bars)
	barplot.legend(frameon=False,fontsize='small')

	# Hide the right and top spines
	barplot.spines['right'].set_visible(False)
	barplot.spines['top'].set_visible(False)
	# Only show ticks on the left and bottom spines
	barplot.yaxis.set_ticks_position('left')
	barplot.xaxis.set_ticks_position('bottom')

	# normalise layout
	plt.tight_layout()

	#show plot (comment out matplotlib.use('Agg'))
	#plt.show()

	# print plot to file (requires matplotlib.use('Agg'))
	filename = plotfile_store + '/' + title.replace(' ','-').replace('/','-').lower() + '-' + datetime.today().strftime('%Y%m%d%H%M%S') + '-' + str(random.randint(1,999999)) + '.png'
	#print filename
	plt.savefig(filename)
	
	# tell calling function where the plot file is
	return filename

# 1 Rolling 12 month crime categories barchart and data
# creates the rolling 12 month category paragraph
def rolling_12_month(region):

	# convert region list to form used in SQL & english
	(sql_region, english_region) = convert_list(region)

	sql = "SELECT distinct \
		concat(upper(left(police_crime.category_name, 1)), lower(right(police_crime.category_name, length(police_crime.category_name) -1)) ) as Category, \
		sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -2 year) and date_add(cast(get_constant('crime-last-updated') as date), interval -1 year), 1, 0) ) as \"" + humanise_date(months_ago(crime_last_updated, 23)) + " to " + humanise_date(months_ago(crime_last_updated, 12)) + "\", \
		sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -1 year) and cast(get_constant('crime-last-updated') as date), 1, 0) ) as \"" + humanise_date(months_ago(crime_last_updated, 11)) + " to " + humanise_date(crime_last_updated) + "\", \
		round(100 * (sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -1 year) and cast(get_constant('crime-last-updated') as date), 1, 0) ) - sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -2 year) and date_add(cast(get_constant('crime-last-updated') as date), interval -1 year), 1, 0) ) ) / sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -2 year) and date_add(cast(get_constant('crime-last-updated') as date), interval -1 year), 1, 0) )) as \"% change between " + humanise_date(months_ago(crime_last_updated, 12)) + " and " + humanise_date(crime_last_updated) + "\" \
	FROM \
		police_crime \
		join place on (place.polygon is not null and st_within(police_crime.location_point, place.polygon)) \
	WHERE  \
		place.name in (" + sql_region + ") \
	GROUP BY 1 \
	HAVING \
		sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -2 year) and date_add(cast(get_constant('crime-last-updated') as date), interval -1 year), 1, 0) ) > 0 \
		OR sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -1 year) and cast(get_constant('crime-last-updated') as date), 1, 0) ) > 0 \
	ORDER BY 3 desc"

	output1 = mysql_sql(sql)
	#print sql
	#print output1

	# plot barchart of crime numbers per category in given region for last 2 yrs
	plot_file = plot_barchart( zip(*output1[1])[1:3], zip(*output1[1])[0], output1[0][1:3], "Crimes per category over last two years in " + english_region,  "Crime categories", "Number of crimes")

	# plot barchart of %age change in crimes per category in given region for each of last 2 yrs (ie 3 vs 2 yrs, 2 vs this year)
	##plot_file = plot_barchart( zip(*output[1])[4:6], zip(*output[1])[0], output[0][4:6], "Percentage change in crimes per category between last 12 months and 12 months before in " + region, "Crime categories", "Percentage")
	##uploaded_file_id = upload_file(plot_file)

	# calculate total crime change

	sql = "SELECT distinct \
		'Total', \
		sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -2 year) and date_add(cast(get_constant('crime-last-updated') as date), interval -1 year), 1, 0) ) as \"" + humanise_date(months_ago(crime_last_updated, 23)) + " to " + humanise_date(months_ago(crime_last_updated, 12)) + "\", \
		sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -1 year) and cast(get_constant('crime-last-updated') as date), 1, 0) ) as \"" + humanise_date(months_ago(crime_last_updated, 11)) + " to " + humanise_date(crime_last_updated) + "\", \
		round(100 * (sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -1 year) and cast(get_constant('crime-last-updated') as date), 1, 0) ) - sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -2 year) and date_add(cast(get_constant('crime-last-updated') as date), interval -1 year), 1, 0) ) ) / sum( if( str_to_date(police_crime.month, '%Y-%m') between date_add(cast(get_constant('crime-last-updated') as date), interval -2 year) and date_add(cast(get_constant('crime-last-updated') as date), interval -1 year), 1, 0) )) as \"% change between " + humanise_date(months_ago(crime_last_updated, 12)) + " and " + humanise_date(crime_last_updated) + "\" \
	FROM \
		police_crime \
		join place on (place.polygon is not null and st_within(police_crime.location_point, place.polygon)) \
	WHERE  \
		place.name in (" + sql_region + ")"

	output2 = mysql_sql(sql)
	#print sql
	#print output2

	#total_previous_year = output2[1][0][1]
	total_last_year = output2[1][0][1]
	total_this_year = output2[1][0][2]
	total_change = output2[1][0][3]
	#print total_change

	# create printable table of data (as HTML table)
	output1[1].extend(output2[1])
	html_data_table = html_table(output1)

	# (func called thus : "filename, html_data_table, total_change = rolling_12_month(region)"
	return [plot_file, html_data_table, total_change, total_last_year, total_this_year, english_region]

# http://matplotlib.org/examples/pylab_examples/stackplot_demo.html
#SQL needs amending to keep in line with above
def rolling_3_month_avg(region):


	# list categories applicable to period
	sql = "select distinct police_crime_category.name \
	from \
	place area  \
	join place crime_place on st_within(crime_place.centre_point, area.polygon)  \
	join relation crime_relation on crime_place.id = crime_relation.minor  \
	join event crime on crime_relation.major = crime.id  \
	join relation category_relation on crime.id = category_relation.major \
	join police_crime_category on category_relation.minor = police_crime_category.id  \
	where   \
	area.name in (" + region + ")"

	output = mysql_sql(sql)
	series = zip(*output[1])[0] # (u'anti social behaviour', u'bicycle theft', u'burglary', u'criminal damage arson', ...)

	sql = "select distinct \
	date_format(crime.date_event, crime.date_resolution) as month, \
	police_crime_category.name as category, \
	count(distinct crime.id) as number \
	from \
	place area  \
	join place crime_place on st_within(crime_place.centre_point, area.polygon)  \
	join relation crime_relation on crime_place.id = crime_relation.minor  \
	join event crime on crime_relation.major = crime.id  \
	join relation category_relation on crime.id = category_relation.major \
	join police_crime_category on category_relation.minor = police_crime_category.id  \
	where   \
	area.name in (" + region + ") \
	group by month, category"

	output = mysql_sql(sql) # [(u'month', u'category', u'number'), [(u'2010-12', u'anti social behaviour', 28), (u'2010-12', u'burglary', 23)... ]
	#print sql
	#print output
	
	# pivot output and calculate 3 month average
	# series already calced (u'anti social behaviour', u'bicycle theft', u'burglary', u'criminal damage arson' ...)
	# xvalues = ('2010-12', '2011-01', '2011-02'...)
	# output data = [(n1, n2, n3... nxvalues), (n4, n5, n6...nxvalues)]; 1 row for each in series where n is a 3 month average
	previous_month = ''
	mount_count = 0
	for row in output[1]:
		# row ~= (u'2010-12', u'anti social behaviour', 28)
		month = row(1)
		print month
		if month == previous_month:
			print DBG
		else:
			mount_count += 1


		# log month from this row for comparison in next loop
		previous_month = month

	#print zip(*output[1])

	#plot_file = plot_barchart( zip(*output[1])[1:4], zip(*output[1])[0], output[0][1:4], "Crimes per category over the last three years in " + region, "Crime categories", "Number of crimes")
	#uploaded_file_id = upload_file(plot_file)


### MAIN ###

# manage commandline args
try:
	opts, args = getopt.getopt(sys.argv[1:], "r:u:p:h:d:o:", ["region=", "user=", "password=", "host=", "database=", "options=" ])
except getopt.GetoptError as err:
	print(err)
	sys.exit(2)

# get commandline options
for o, a in opts:
	if o in ("-r", "--region"):
		region = a
	elif o in ("-u", "--user"):
		user = a
	elif o in ("-p", "--password"):
		password = a
	elif o in ("-h", "--host"):
		host = a
	elif o in ("-d", "--database"):
		database = a
	elif o in ("-o", "--options"):
		options = a

# check for required parms
if region is None or user is None or password is None or host is None or database is None:
	print('ERR: Specify all parameters')
	sys.exit(1)

# test connection to database
try:
	db = mysql.connector.connect(user = user, password = password, host = host, database = database)
except:
	print('ERR: Unable to connect to database "' + database + '" with user "' + user + '"' )
	sys.exit(1)
#print('INF: Connection to DB : OK')

# calculate relevant dates
crime_last_updated = standardise_date(mysql_function('get_constant', ['crime-last-updated']))

# create rolling 12 month graph and data
(rolling_12_month_graph_filename, rolling_12_month_html_data_table, total_change, total_last_year, total_this_year, english_region) = rolling_12_month(region)

# create JSON string output to be used by Huginn
if total_change > 0:
	increased_decreased = 'increased by ' + str(abs(total_change)) + '%'
elif total_change < 0:
	increased_decreased = 'decreased ' + str(abs(total_change)) + '%'
else:
	increased_decreased = 'not changed'

JSON_string = ' {' + \
' "ward":"' + region + '",' + \
' "title":"Crime statistics for ' + english_region + ' ward in ' +  humanise_date(crime_last_updated) + '",' + \
' "graphic":"[IMG1]",' + \
' "intro_para":"Overall reported crime in ' + english_region + ' ward has ' + increased_decreased + ' between the 12 months ending ' + humanise_date(months_ago(crime_last_updated, 12)) + ' and the 12 months ending ' + humanise_date(crime_last_updated) + ', according to crime statistics <a href=https://www.police.uk/ target=_blank>released by the Home Office</a>.",' + \
' "body_para":"This table shows the same data as the graph, with a total at the bottom.<br>' +  rolling_12_month_html_data_table + '",' + \
' "notes_list":"<li><em>Data is sourced from <a href=https://data.police.uk/ target=_blank>data.police.uk</a> who say this data is subject to alteration, and locations are approximated.</em></li><li><em>Minor discrepancies in per-area totals between the <a href=https://www.police.uk/thames-valley/ target=_blank>police mapping tool</a> and that shown here are usually because a crimes <a href=https://data.police.uk/about/#anonymisation target=_blank>anonymised location</a> is given as the middle of a public road forming the boundary between two areas.</em></li><li><em>Changes in crime numbers may be artefactual; a change in category definitions or reporting protocols, for example.</em></li> <li><em>Data may be released with more than a months delay. The data shown here is the <a href=https://data.police.uk/changelog/ target=_blank>most recently released</a> at the time of publication.</em></li><li><em>Police neighbourhood boundaries <a href=https://data.police.uk/data/boundaries/ target=_blank>may change each month</a> and are not the same as ward boundaries. This article uses the more stable ward boundaries.</em></li>",' + \
' "link_list":"<li><a href=https://www.police.uk/thames-valley/#neighbourhoods target=_blank>Neighbourhood crime statistics</a></li> <li><a href=https://data.police.uk/ target=_blank>Source data</a></li>",' + \
' "files":"' + rolling_12_month_graph_filename + '"' + \
' }'

# output JSON stromg ready for Huginn de-stringifier
print (JSON_string)
