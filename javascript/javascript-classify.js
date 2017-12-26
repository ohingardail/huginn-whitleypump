Agent.receive = function() {

	// assemble search terms
	var search_objects = {
		postcode	: this.credential('data-postcode-town-constituency-ward-road'),
		road		: this.credential('data-road-town-constituency-ward-postcode'),
		ward		: this.credential('data-ward-town-constituency'),
		organisation	: this.credential('data-organisation-type-town-constituency-ward-road-postcode'),
		person		: this.credential('data-person-type-organisation-town-constituency-ward-road-postcode')
	}

	var events = this.incomingEvents();
  
	for (var i = 0; i < events.length; i++) {
		var event_string = JSON.stringify(events[i].payload) // the entire event as a (regex searchable) string
		var found_list = []

		// perform mandatory 'reading' test
		if (event_string.search(/\bReading(?!.*Pennsylvania)/g) > 0)
		{
			found_list.push({town:"Reading"})
		}
    
		// wind through regex list
		var search_object_names=Object.keys(search_objects)
		for (var r = 0; r < search_object_names.length; r++) 
		{
			var search_type=search_object_names[r].trim() //'postcode' 'ward' 'road' etc
			var search_table=JSON.parse(search_objects[search_type]) // array ('table') of search objects: '[{postcode:A, ward:B}{postcode:C, ward:D}]'

			//this.log("search_object : " + JSON.stringify(search_object) )

			// for each 'row' in 'table' of search objects
			for (var s = 0; s < search_table.length; s++)
			{
				var search_row = search_table[s]
				//var search_column_names=Object.keys(search_row)

				// generalise search term
				var search_term_regex = search_row[search_type].trim()

				// generalise search term specifically for each type
				switch (search_type) 
				{
					case 'postcode':
						break;
					case 'road':
						search_term_regex=search_term_regex.replace(/\broad\b/ig, 	'r(?:oa)?d')
						search_term_regex=search_term_regex.replace(/\bstre\+t\b/ig, 	'st(?:re+t)?')
						search_term_regex=search_term_regex.replace(/\bgardens\b/ig, 	'g(?:ar)?de?ns?')
						search_term_regex=search_term_regex.replace(/\bclose\b/ig, 	'clo?se?')
						search_term_regex=search_term_regex.replace(/\blane\b/ig, 	'la?ne?')
						search_term_regex=search_term_regex.replace(/\bcourt\b/ig, 	'c(?:our)?t')
						search_term_regex=search_term_regex.replace(/\bavenue\b/ig, 	'ave(?:nue)?')
						search_term_regex=search_term_regex.replace(/\bway\b/ig, 	'wa?y')
						search_term_regex=search_term_regex.replace(/\bgrove\b/ig, 	'gro?ve?')
						search_term_regex=search_term_regex.replace(/\bcrescent\b/ig, 	'cresc(?:ent)?')
						search_term_regex=search_term_regex.replace(/\bdrive\b/ig, 	'dr?i?ve?')
						search_term_regex=search_term_regex.replace(/\bplace\b/ig, 	'pla?c?e?')
						search_term_regex=search_term_regex.replace(/\bsquare\b/ig, 	'sq(?:uare)?')
						search_term_regex=search_term_regex.replace(/\bterrace\b/ig, 	'terr(?:ace)?')
						break;
					case 'ward':
						break;
					case 'person':
						break;
				} // switch (search_type) 

				var search_term_regex = '\\b' + search_row[search_type].trim().replace(/\s+/g, '\\s+').replace(/(.)\1+/ig, '$1+').replace('-', '[ -]?') + '\\b'

				//this.log("search_term_regex : " + search_term_regex )

				if (search_term_regex.length > 0)
				{
					// construct the regex
					var regex=new RegExp(search_term_regex, 'ig')

					// do the search
					if (event_string.search(regex) > 0 )
					{
						found_list.push(search_table[s])
					}
				} // if (search_term_regex.length > 0)

			} // for (var s = 0; s < search_table.length; s++)
     
		} // for (var r = 0; r < search_object_names.length; r++) 

		//this.log("found_list=" + JSON.stringify(found_list))

		// amalgamate found object
		var found = {}
		for (var f = 0; f < found_list.length; f++)
		{
			//this.log("found_list[" + f + "]=" + found_list[f] )
			var found_list_keys=Object.keys(found_list[f])
			//this.log("found_list_keys=" + found_list_keys )

			for (var k = 0; k < found_list_keys.length; k++)
			{
				var key=found_list_keys[k]
				//this.log("found_list["+ f + "]["+ key + "]=" + found_list[f][key] )
				var value=found_list[f][key].trim()
				//this.log(key + " = " + value )

				if ( value.length > 0 )
				{
					if ( key in found  )
					{
						//this.log("found["+ key+ "]=" + found[key] )
						var value_term_regex = '\\b' + value.replace(/\s+/g, '\\s+').replace(/(.)\1+/ig, '$1+').replace('-', '[ -]?') + '\\b'
						//this.log("value_term_regex=" + value_term_regex )
						var value_regex = new RegExp(value_term_regex, 'ig')
						
						if (found[key].search(value_regex) < 0 )
						{
							found[key] = found[key] + "," + value
						//} else {
						//	this.log(value + " already added")
						}
					} else {
						found[key] = value
					}
				}
			}
		}
		
		//this.log("found=" + JSON.stringify(found))

		// append to event
		if (Object.keys(found).length > 0)
		{
			events[i].payload.found = found
		}

		// emit new event
		this.createEvent(events[i].payload);

	} // for (var i = 0; i < events.length; i++)
}
