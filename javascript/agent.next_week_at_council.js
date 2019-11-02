{% credential javascript_library %}

Agent.receive = function() {

  var incomingEvents = this.incomingEvents();
  for(var i = 0; i < incomingEvents.length; i++) 
  {
	agendaItems = incomingEvents[i].payload.events.sort(
								by('unixDate', false, parseInt,
									by('title', false,
										function (x) {return x.toUpperCase().replace(/\W/g, '');},
										by('agenda_item', false, parseInt)
									)
								)
							);
	var committeeList = []
	var wardList = []
	var linkList = []
	var agendaHtml=''
	var lastTitle=''
	// var earliestDate=''

	for(var a = 0; a < agendaItems.length; a++)
	{
		agendaItem = agendaItems[a]
		//this.log("agendaItems["+ a + "]=" + JSON.stringify(agendaItem) )

		// if (earliestDate.length > 0 ){
		// 	earliestDate = agendaItem.start_dateTime.replace(/^([0-9]+\s+\w+)\b.*/, '$1')
		// }

		var currentWards = agendaItem.found.ward.split(",")
		currentWards = sortUnique(currentWards)
		for(var w = 0; w < currentWards.length; w++)
		{
			wardList.push(currentWards[w].trim())
		}
		var englishCurrentWards = currentWards.join(", ") + " ward"
		if (currentWards.length > 0 ){
			englishCurrentWards = englishCurrentWards.replace(/,\s*([\w\s]+ward)$/, ' and $1s')
		}

		// format committee date into standard English
		var cmteDate = new Date(agendaItem.unixDate * 1000)
		var englishDatetime = " at " + 
			(cmteDate.getHours() > 12 ? cmteDate.getHours() - 12 : cmteDate.getHours() ) + 
			(cmteDate.getMinutes() != 0 ? '.' + ("00" + cmteDate.getMinutes()).slice(-2) : '' ) + 
			(cmteDate.getHours() > 12 ? 'pm' : 'am' ) + 
			" on " + 
			cmteDate.getDate() + " " + 
			monthNames[cmteDate.getMonth()]

		var currentTitle = agendaItem.title.trim()
		if ( lastTitle.length == 0 || lastTitle != currentTitle) 
		{
			committeeList.push(currentTitle)
			if (agendaHtml.length > 0) {
				agendaHtml += '</table>'
			}
			agendaHtml += '<h5><a href=' + encodeURI(agendaItem.source_url.trim()) + ' target=_blank rel="noopener noreferrer">' + currentTitle + '</a>' + englishDatetime + '.</h5>'
			// agendaHtml = agendaHtml + '<a href="https://www.google.co.uk/maps/place/' + agendaItem.location1.replace(/,/g, '').replace(/\s+/g, '+') + '" target="_blank">' + properCase(agendaItem.location) + ', ' + agendaItem.location1 + '</a>. <table>'
			agendaHtml += '<em>' + properCase(agendaItem.location).replace(/\b([A-Z]{2}[0-9]{1,2}\s+[0-9][A-Z]{2})\b/i, function(v) { return v.toUpperCase(); }) + '</em>. <table>'
			linkList.push('<a href=' + encodeURI(agendaItem.source_url.trim()) + ' target=_blank rel="noopener noreferrer">' + currentTitle + englishDatetime + '</a>') 
		}

		agendaHtml += '<tr><td style=vertical-align:top;padding:10px>'
		agendaHtml += '<strong>Item&nbsp;' + agendaItem.agenda_item.trim() + '</strong>'

// <ul> <li><a href=\"https://democracy.reading.gov.uk/mgIssueHistoryHome.aspx?IId=3973\" title=\"Link to issue details for item 8.\">View the background to item 8.</a></li> </ul>
// .replace('<ul>\s*<li>\s*(<a\s+.*?\bView\s+the\s+background\b.*?<\/a>)\s*<\/li>\s*<\/ul>', '$1')

		// "<td><pre></pre></td>" adds a spacer between col1 & 2 (otherwise WP crams them together)
		//agendaHtml += '</td><td style=vertical-align:top><pre>&nbsp;</pre></td>'
		agendaHtml += '<td style=vertical-align:top;padding:10px>'
		agendaHtml += '<i>'+ englishCurrentWards + '</i><br>' 

		// munge agenda description
		var agenda_description = agendaItem.agenda_description
		agenda_description = agenda_description.replace(/<td(.*?)>/ig, '<td style=vertical-align:top;padding:10px>')
		agenda_description = agenda_description.replace(/\s+pdf\s+[0-9]+\s*[gmk]b\s*<\/a>/ig, '</a>')
		//agenda_description = agenda_description.replace(/<ul>\s*<li>\s*(<a\s+.*?\<\/a>)\s*<\/li>\s*<\/ul>/ig, '$1<br>')
		agenda_description = agenda_description.replace(/<\/li>/ig, '<br>')
		agenda_description = agenda_description.replace(/<\/?[ou]?li?>/ig, '')
		agenda_description = agenda_description.replace(/\bsui\s+generis\b/ig, '<em>sui generis<\/em>')
		agenda_description = agenda_description.replace(/<p>/ig, '')
		agenda_description = agenda_description.replace(/<\/p>/ig, '<br>')
		agenda_description = agenda_description.replace(/<\.+/g, '.')
		agenda_description = agenda_description.replace(/(?:<br>\s*)+/ig, '<br>')
		agenda_description = agenda_description.replace(/<br>\s*$/ig, '')
		agenda_description = agenda_description.replace(/<br>\s*<br>/ig, '<br>')
		// this also replaces dddddd with url when dddddd is already within a url
		//agenda_description = agenda_description.replace(/\s+(\d{6})\b/ig, '<a href=http://planning.reading.gov.uk/fastweb_PL/detail.asp?AltRef=$1 target=_blank>$1<\/a>')

		// append decription
		agendaHtml += agenda_description.trim()
		agendaHtml += '</td></tr>' 

		lastTitle = currentTitle
	} // for(var a = 0; a < agendaItems.length; a++)

	committeeList = sortUnique(committeeList)
	wardList = sortUnique(wardList)
	linkList = sortUnique(linkList)
	agendaHtml = agendaHtml + '</table>'

  } //for(var i = 0; i < incomingEvents.length; i++) 

  //this.log(committeeList)
  //this.log(wardList)
  //this.log(agendaHtml)

  var candidateImages = [10928, 11201].sort( function() { return 0.5 - Math.random() } );

  var englishWardList = wardList.join(", ") + " ward"
  if (wardList.length > 0 ){
	englishWardList = englishWardList.replace(/,\s*([\w\s]+ward)$/, ' and $1s')
  }

  var englishCommitteeList = committeeList.join(", ").toLowerCase().replace(/\s*(?:sub\s*-?\s*)?com+it+e+\s*/ig, '') + " committee"
  if (committeeList.length > 0 ){
	englishCommitteeList = englishCommitteeList.replace(/[0-9]+\b/g, '').replace(/,\s*([\w\s]+committee)$/, ' and $1s')
  }

  //afterword = "<br>The order of agenda items may be changed to prioritise applications with public speakers."
  afterword = ""
  linkList.push('<a href=http://webcast.nl/readingboroughcouncil/ target=_blank rel="noopener noreferrer">Reading Borough Council webcasting</a>') 

  this.createEvent(
      { 
      "title" : "Reading Borough Council discusses south Reading at " + englishCommitteeList + " this week",
      "body" : "[gallery type=rectangular ids=" + candidateImages[1].toString() + " orderby=rand]<br> <a href=http://www.reading.gov.uk target=_blank rel='noopener noreferrer'>Reading Borough Council</a> will be discussing issues in south Reading during " + englishCommitteeList + " next week. <!--more-->" + agendaHtml + afterword + "<hr><h5>Links</h5><ol><li>" + linkList.join("</li><li>") + "</li></ol>",
      "category" : "Reading Borough Council, politics, " +  wardList.join(" ward, ") + " ward",
      "delay" : today.getDate() + "-" + monthNames[today.getMonth()] + "-" + today.getFullYear() + " 15:00:00",
      "status" : "pending"
	}
   )
}
