{% credential javascript_library %}

Agent.receive = function() {

	var incomingEvents = this.incomingEvents();
	for(var i = 0; i < incomingEvents.length; i++) {

   		endpointItems = incomingEvents[i].payload.events.sort(
								by(	'endpoint', 
									false, 
									function (x) {return x.toString().toUpperCase().replace(/\W/g, '');},
									by('page', false, parseInt)
								)
							);

		// this.log("endpointItems=" + JSON.stringify(endpointItems));

		var previousEndpoint = ''
		var currentEndpoint = ''
		var endpointList = []
		var endpointIdList = []
		// var endpoint_object = {}
		//this.log("endpointItems.length=" + endpointItems.length)

		for(var a = 0; a < endpointItems.length; a++)
		{
			endpointItem = endpointItems[a]
			//this.log("endpointItem=" + JSON.stringify(endpointItem));
			currentEndpoint = endpointItem.endpoint.toString().trim()

			// if endpoint has changed, then emit event (this shouldn't ever happen!)
			if ( previousEndpoint.length > 0 && previousEndpoint != currentEndpoint ) 
			{
				this.createEvent(
				      	{ 
					      "endpoint" : previousEndpoint, 
					      "body" : JSON.stringify( endpointList )
					}
				)
				endpointList = []
				endpointIdList = []	
			}

			// extract id and name only from 'body' and append to list
			var response = parseResponse(endpointItem)
			//this.log("response=" + JSON.stringify(response));
			if ( response.length > 0)
			{
				for(var r = 0; r < response.length; r++)
				{
					//this.log("response[" + parseInt(r) + "]=" + JSON.stringify(response[r]))
					if (endpointIdList.includes(response[r]['id']) === false) // dont process dupes
					{
						var endpointObject = 
							{
								"id" : response[r]['id']
							}
							
						if ( 'name' in response[r] )
						{
						  endpointObject['name'] = response[r]['name']
						}
						else if ( 'title' in response[r] ) 
						{
					    endpointObject['title'] = response[r]['title']['rendered']
					    
					    if ( 'link' in response[r] )
					  	{
					  	  endpointObject['link'] = response[r]['link']
					  	}
						}
						
						//this.log("endpointObject=" + JSON.stringify(endpointObject))
						endpointList.push(endpointObject)
						endpointIdList.push(response[r]['id']) // keep tally of ids
					}
				}
			}

	   	previousEndpoint = currentEndpoint
		}

		// emit event
		//this.log("endpointList.length=" + endpointList.length)
		this.createEvent(
		      	{ 
			      "endpoint" : currentEndpoint, 
			      "body" : JSON.stringify( endpointList )
			}
		)
	}
}
