{% credential javascript_library %}

Agent.receive=function()
{
 var in_events = this.incomingEvents();
 for(var i = 0; i < in_events.length; i++)
  {
    var response = parseResponse(in_events[i])
    var key = "wpsg_" + in_events[i].payload.endpoint
    //this.log(Object.keys( response ).length)
    if (response != null && Object.keys( response ).length > 0)
    {
      //this.log(response)
      var out_event = {};
      //this.credential(key, '{}')
      if (key == 'wpsg_token')
      {
        var value = response.token
      } else {
        var value = JSON.stringify( response )
      }
      out_event['credential'] = key + " = " + value
      this.createEvent( out_event );
    }
  }
}
