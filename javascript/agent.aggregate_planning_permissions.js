{% credential javascript_library %}

Agent.receive = function() {

  var incomingEvents = this.incomingEvents();
  for(var i = 0; i < incomingEvents.length; i++) 
  {
	applicationItems = incomingEvents[i].payload.events.sort(
									by('ward', false, function (x) {return x.toUpperCase().replace(/\W/g, '');},
										by('application_number', false, parseInt)
									)
								);
	var wardList = []
	var linkList = []
	var applicationHtml=''
	var lastWard=''

	for(var a = 0; a < applicationItems.length; a++)
	{
		applicationItem = applicationItems[a]
		//this.log("applicationItem["+ a + "]=" + JSON.stringify(applicationItem) )

		wardList.push(applicationItem.ward.trim())
		var currentWard = applicationItem.ward.trim()

		// add the ward heading
		if ( lastWard.length == 0 || lastWard != currentWard) 
		{
			applicationHtml = applicationHtml + '<h5>' + properCase(currentWard) + ' ward</h5>'	
		}

		// add the map
		applicationHtml += '<div style="width: 50%; padding: 5px; float: left;">[googlemaps https://www.google.com/maps/embed/v1/place?key=' + 
			this.credential('google_maps_api_key') + '&amp;q=' + 
			applicationItem.full_address.trim().replace(/\b([0-9]+)\s*[-–]\s*[0-9]+\b/, '$1').replace(/^land\s+.*?(north|south|east|west|adjacent|corner)\s*(to|of)?\s+/i, '').replace(/^site\s+of\s+/i, '').replace(/^(flat|apartment)\s+([A-Z]|[[:digit:]]+)?\s*/i, '').replace(/&amp;/g, 'and').replace(/<br>/g, '+').replace(/(\W|[[:punct:]]|\+)+/g, '+') + '&amp;h=200&amp;w=200]</div>'

		// add the text
		applicationHtml += '<div style="width: 50%; padding: 5px; float: right;"><br><br><strong>' + applicationItem.type + ' <a href=' + applicationItem.source_url + ' target=_blank rel="noopener noreferrer">' + applicationItem.application_number + '</a>.</strong><br>' 
		applicationHtml += '<em>' + applicationItem.full_address.trim().replace(/\s*\.*$/, '.').replace('  ', '<br>') + '</em><br><br>' 

		// clean up then add the description
		//var description = applicationItem.description.replace(/\b(\d{6})\b/g, '<a href=http://planning.reading.gov.uk/fastweb_PL/detail.asp?AltRef=$1 target=_blank rel="noopener noreferrer">$1</a>') // cant be sure its not a building control ref
		var description = applicationItem.description.replace(/\u00D7/g, 'x').replace(/(?:\s|^)(\d)x?(?!\.)\b/g, function (match, capture) { return " " + cardinalNumbers[ capture ] } )

		//.replace(/\b1\s*x\b/g, 'one').replace(/\b2\s*x\b/g, 'two').replace(/\b3\s*x\b/g, 'three').replace(/\b4\s*x\b/g, 'four').replace(/\b5\s*x\b/g, 'five')
//replace(/\b(?<!\.)(\d)x?(?!\.)\b/g
		// this.log("number=" + cardinalNumbers['5'] )

		applicationHtml += description.replace(/\s+/, ' ').replace(/\s*\.*$/, '.').trim() + '<br>'

		// add the postcode search
		if (applicationItem.postcode.length > 0 && applicationItem.postcode != '') {
			applicationHtml += '<br><br>See all planning applications at <a href=https://whitleypump.wordpress.com/category/reading-borough-council/planning-applications/?s=' + applicationItem.postcode.replace(/\s+/g, '+') + ' target=_blank rel="noopener noreferrer">' + applicationItem.postcode + '</a>.'
		}

		// round off div
		applicationHtml += '</div><div style=clear:both;></div><hr />'

		lastWard = currentWard
	} // for(var a = 0; a < applicationItems.length; a++)

	// get unique, sorted list of affected wards
	wardList = sortUnique(wardList)

  } //for(var i = 0; i < incomingEvents.length; i++) 

  // var candidateImages = [891, 4661].sort( function() { return 0.5 - Math.random() } );

  if ( applicationHtml.length > 0 )
  {

	  var today = new Date()
	  var tomorrow = new Date()
	  tomorrow.setDate(today.getDate() + 1)

	  var englishWardList = wardList.join(", ") + " ward"
	  if (wardList.length > 0 ){
		englishWardList = englishWardList.replace(/,\s*([\w\s]+ward)$/, ' and $1s')
	  }

	  ///afterword = "<br>The order of agenda items may be changed to prioritise applications with public speakers."
	  linkList.push('Reading Borough Council <a href=https://democracy.reading.gov.uk/mgCommitteeDetails.aspx?ID=143 target=_blank rel="noopener noreferrer">planning applications committees</a>')
	  linkList.push('Reading Borough Council <a href=https://planning.reading.gov.uk target=_blank rel="noopener noreferrer">planning portal</a>')
	  linkList.push('Reading Borough Council <a href=http://www.reading.gov.uk/planning target=_blank rel="noopener noreferrer">planning documentation</a>')

	  this.createEvent(
	      { 
	      "title" : "Planning and building control applications in south Reading for the week ending " + today.getDate() + " " + monthNames[today.getMonth()], 
	      "body" : "There " + (applicationItems.length > 1 ? "were " : "was ") + (applicationItems.length < cardinalNumbers.length ? cardinalNumbers[applicationItems.length] : applicationItems.length ) + " new planning or building control application" + (applicationItems.length > 1 ? "s" : "") + " in south Reading this week. " + (applicationItems.length > 1 ? "They " : "It ") + "may be discussed at one of the next Reading Borough Council <a href=https://democracy.reading.gov.uk/mgCommitteeDetails.aspx?ID=143  target=_blank>planning applications committees</a>.<br><!--more-->" + applicationHtml + "<h5>Links</h5><ol><li>" + linkList.join("</li><li>") + "</li></ol>",
	      "category" : "Reading Borough Council, news, planning applications, " +  wardList.join(" ward, ") + " ward",
	      "delay" : today.getDate() + "-" + monthNames[today.getMonth()] + "-" + today.getFullYear() + " 20:00:00",
	      "status" : "pending"
		}
	   )
  }
}
