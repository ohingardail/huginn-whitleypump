{% credential javascript_library %}

Agent.receive = function() {

	var incomingEvents = this.incomingEvents();
	for(var i = 0; i < incomingEvents.length; i++) 
	{
		var term_dates = incomingEvents[i].payload.term_dates.split('\n')
		var start_date = null
		var end_date = null
      
		for(var t = 0; t < term_dates.length; t++) 
		{
			// this.log("term_dates[" + t.toString() + "]=" + term_dates[t] );

			// 'Wednesday 5 September 2018' to '2018-09-05'
			//term_date_string = term_dates[t].split(' ')[3] + '-' + term_dates[t].split(' ')[2] + '-' + term_dates[t].split(' ')[1]
			
			if ( t > 0) 
			{
				if ( start_date == null )
				{
					start_date = new Date(term_dates[t])
					start_date.setDate(start_date.getDate() + 1) // start of holiday is day after end of term
			  		// this.log("start_dateTime=" + start_date.toString());
				} 
				else if ( start_date != null && end_date == null )
				{
					end_date = new Date(term_dates[t])
					//end_date.setDate(end_date.getDate() - 1) // end of holiday is day before start of term
					// this.log("end_date=" + end_date.toString() );
				} 
				    
				if ( start_date != null && end_date != null )
				{

					this.createEvent(
						{ 
						"title": "School holiday",
						"start_dateTime": start_date.getDate() + " " + monthNames[start_date.getMonth()] + " " + start_date.getFullYear(),
						"end_dateTime": end_date.getDate() + " " + monthNames[end_date.getMonth()] + " " + end_date.getFullYear(),
						"source_url": incomingEvents[i].payload.source_url,
						"mandatory_calendar": "default",
						"default_duration": 86400,
						"location": "Reading",
						"description": "School holiday"
						}
					)

					// reset
					start_date = null
					end_date = null
			    	}
				    
			} // if ( t > 0) 
		}
  	} // for(var i = 0; i < incomingEvents.length; i++) 
}
