{% credential javascript_library %}

Agent.receive = function() {

	var weekStartDay = "Monday"
	//var weekStart = new Date() 
	var weekStart = nextDOW( weekStartDay ) // date calendar starts
	var weekStartUnixDate = getUnixDate(weekStart)
	//this.log("From:" + weekStart + '(' + weekStartUnixDate + ')')

	//var weekEnd = new Date() 
	var weekEnd = nextDOW( weekStartDay, true, weekStart) // date calendar ends
	var weekEndUnixDate = getUnixDate(weekEnd)
	// this.log("To:" + weekEnd + '(' + weekEndUnixDate + ')')

	//var dateString = weekStart.getDate() + " " + monthNames[weekStart.getMonth()]
	var pubDate = new Date() 
	pubDate.setDate(weekStart.getDate() - 1) 
	// this.log("Pub:" + pubDate )

	var incomingEvents = this.incomingEvents(); 

	// for each incoming event (usually just one giant event)
	for(var i = 0; i < incomingEvents.length; i++)
	{
		var calendarItems = incomingEvents[i].payload.events.sort( by('unixDate', false ) );
		var calendarString = ''
		var previousCalendarDayString = ''

		for(var n = 0; n < calendarItems.length; n++)
		{
			var calendarItem = calendarItems[n];

			// only process events between (and inc) nextMonday and nextMondayNext
			if ( calendarItem.unixDate.length > 0 && parseInt(calendarItem.unixDate) >= weekStartUnixDate && parseInt(calendarItem.unixDate) <= weekEndUnixDate )
			{
				// this.log(calendarItem.unixDate)

				dateJS = convertUnixDate(calendarItem.unixDate)
				calendarDayString = dayNames[dateJS.getDay()] + ' ' + dateJS.getDate() + ' ' + monthNames[dateJS.getMonth()]
				calendarTimeString = dateJS.getHours() + ':' + ('0' + dateJS.getMinutes()).slice(-2)
				
				if ( previousCalendarDayString.length == 0 || calendarDayString != previousCalendarDayString )
				{
					calendarString += '<tr><td style="text-align:left;vertical-align:top;" colspan=2><h5>' + calendarDayString + '</h5></td></tr>'
				}
				previousCalendarDayString = calendarDayString
				
				calendarString += '<tr><td style="text-align:left;vertical-align:top;padding:5px;">' + calendarTimeString + '</td>'
				
				calendarString += '<td style="text-align:left;vertical-align:top;padding:5px;">'
				if (calendarItem.data_url.length != 0 )
				{
					calendarString += '<a href="' + calendarItem.data_url + '" target="_blank" rel="noopener noreferrer">' + calendarItem.summary + '</a>'
				}
				else if( calendarItem.source_url.length != 0 )
				{
					calendarString += '<a href="' + calendarItem.source_url + '" target="_blank" rel="noopener noreferrer">' + calendarItem.summary + '</a>'
				}
				else
				{
					calendarString += calendarItem.summary
				}

				if (calendarItem.location.length != 0 )
				{
					calendarString += '<br><em>' + calendarItem.location.replace(/,?\s+((east\s+|west\s+)?berkshire|united\s+kingdom|uk)\b/i, '').trim() + '</em>'
				}

				calendarString += '</td></tr>'
			}

		} // for(var n = 0; n < calendarItems.length; n++)

	} // for(var i = 0; i < incomingEvents.length; i++)

	if ( calendarString.length > 0 )
	{

		var candidateImages = JSON.parse(this.credential('imagelist_whatson')).sort( function() { return 0.5 - Math.random() } );
		calendarString = '<table>' + calendarString + '</table>'

		this.createEvent(
			{
			"title" : "What’s happening in Katesgrove and Whitley from " + weekStart.getDate() + " " + monthNames[weekStart.getMonth()],
			"body" : "[gallery type=\"rectangular\" ids=\"" + candidateImages[1].toString() + "," + candidateImages[2].toString() + "\" orderby=\"rand\"]<br><!--more-->" + calendarString + "The <a href=\"https://whitleypump.wordpress.com/whats-on/\" target=\"_blank\">What’s On</a> page shows events over the coming months.<br><br>You are advised to confirm dates, times and prices with whoever is organising the event. Although <em>The Whitley Pump</em> takes care to get event details correct, we can take no responsibility for errors, omissions or cancellations, however caused.<br><br>You can get reminders of these events by subscribing to our <a href=\"https://twitter.com/whitleypump\" target=\"_blank\" rel=\"noopener noreferrer\">Twitter</a> feed.",
			"category" : "Art &amp; culture, Museums, Katesgrove ward, Redlands ward, Whitley ward",
			"delay" : pubDate.getDate() + "-" + monthNames[pubDate.getMonth()] + "-" + pubDate.getFullYear() + " 20:00:00"
			}
		);
	}
};

