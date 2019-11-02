Agent.receive = function() {
  var events = this.incomingEvents();
  
  // wind through each event
  for(var e = 0; e < events.length; e++) 
  {
    //this.log("SET CREDENTIAL TO:" + events[e].payload.credential)
    // this.log(events[i].payload.credential.replace(/'/g, '"'))
    
    // if there is a 'credential' tag...
    if ('credential' in events[e].payload && events[e].payload.credential.length > 0)
    {
      // convert credentials to array if not one already
      new_credential=[]
      if (isArray(events[e].payload.credential))
      {
        new_credential=events[e].payload.credential
      } else
      {
        new_credential=[events[e].payload.credential]
      }

      // initialise merged object
      merged_credential_object=[]

      // wind through each credential in array
      for (var n = 0; n < new_credential.length; n++)
      {
      
        //this.log("CREDENTIAL [" + n + "]: " + new_credential[n])

        new_credential_variable=new_credential[n].split('=')[0].trim()
      	//this.log("CREDENTIAL VARIABLE " + n + ": " + new_credential_variable)
      
      	new_credential_value=""
      	for(var c=1; c < new_credential[n].split('=').length; c++)
      	{
      	  if (new_credential_value.length == 0 )
      	  {
      		  new_credential_value=new_credential[n].split('=')[c].trim()
      	  } else {
      	    new_credential_value=new_credential_value + "=" + new_credential[n].split('=')[c].trim()
      	  }
      	}
      	// this.log("CREDENTIAL VALUE [" + n + "]: " + new_credential_value)

        old_credential_value=this.credential(new_credential_variable)

      	// credential value may be simple "ABC" or complex '{"A":"B","C":"D"}' or horrifically complex '[{"A":"B"},{"C":"D"}]'
      	if ( isJsonString(new_credential_value) )
      	{
      		// complex value - assemble merged object
      		//this.log("COMPLEX")
       		new_credential_value_object=JSON.parse(new_credential_value)
      
      		// treat as table (replace entire table)
       		if (isArray(new_credential_value_object))
      		{
      		  //this.log("ARRAY")
      			this.credential(new_credential_variable, new_credential_value)        
      			// this.log("SAVED CREDENTIAL:" + new_credential_variable + " VALUE:" + new_credential_value)
      
      		} else {
      
      			// treat as row in table (update value keyed on variable)
      			if ( new_credential_value_object in merged_credential_object )
      			{
      				// merge with previously updated new credential
      				merged_credential_object[new_credential_variable]=object_merge(merged_credential_object[new_credential_variable], new_credential_value_object)
                 
      			} else {
      
      				// merge with old credential (if there is one)
      				if ( old_credential_value == null || old_credential_value.length == 0 )
      				{
      					merged_credential_object[new_credential_variable]=new_credential_value_object
      
      				} else {
      					old_credential_object=JSON.parse(old_credential_value)
      					merged_credential_object[new_credential_variable]=object_merge(old_credential_object, new_credential_value_object)
       
      				} // if ( old_credential_value == null || old_credential_value.length == 0 )
      
      			} //if ( new_credential_variable in merged_credential_object )
      		} // if (isArray(new_credential_value_object))
      
         } else {

      		// simple value- just write it straight out (if its different)
      	  	//this.log("SIMPLE")
      		if ( old_credential_value == null || old_credential_value.length == 0 || old_credential_value != new_credential_value )
      		{
      			this.credential(new_credential_variable, new_credential_value)        
      			// this.log("SAVED CREDENTIAL:" + new_credential_variable + " VALUE:" + new_credential_value)
      
      		} // if ( old_credential_value == null || old_credential_value.length == 0 || old_credential_value != new_credential_value )

	      } // if ( isJsonString(new_credential_value) )

      } // for (var n = 0; n < credential.length; n++)

      // write all elements of merged key to huginn credentials
      merged_keys=Object.keys(merged_credential_object)
      for(var m = 0; m < merged_keys.length; m++) 
      {
        merged_key=merged_keys[m]
        old_value=this.credential(merged_key)
        new_value=JSON.stringify(merged_credential_object[merged_key])
        if ( old_value == null || old_value.length == 0 || old_value != new_value )
        {
          this.credential(merged_key, new_value)
          // this.log("SAVED CREDENTIAL:" + merged_key + " VALUE:" + new_value)
        } // if ( old_value == null || old_value.length == 0 || old_value != new_value )
      } // for(var m = 0; m < merged_keys.length; m++) 

    } // if ('credential' in events[e].payload && events[e].payload.credential.length > 0)
  } // for(var e = 0; e < events.length; e++)
} // Agent.receive = function()
