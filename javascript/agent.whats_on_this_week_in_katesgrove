Agent.check = function() {
  
var monthNames = [
  "January", "February", "March",
  "April", "May", "June", "July",
  "August", "September", "October",
  "November", "December"
];
  
var today = new Date()
var tomorrow = new Date()
var nextweek = new Date()

tomorrow.setDate(today.getDate() + 1)
nextweek.setDate(today.getDate() + 7)

dateString = tomorrow.getDate() + " " + monthNames[tomorrow.getMonth()] + " to " + nextweek.getDate() + " " + monthNames[nextweek.getMonth()]

    this.createEvent(
      { 
      "title" : "What’s happening on Katesgrove Hill from ".concat(dateString),
      "body" : "[gallery type=\"rectangular\" ids=\"921,919,681,221,5126,4512,4513,1484\" orderby=\"rand\"]<br>Click any entry to find more about an event. The <a href=\"https://whitleypump.wordpress.com/whats-on/\" target=\"_blank\">What’s On</a> page shows events over the coming months.<br><!--more--><br>[googleapps domain=\"calendar\" dir=\"calendar/embed\" query=\"showTitle=0&amp;showNav=1&amp;showDate=0&amp;showPrint=0&amp;showTabs=0&amp;showCalendars=0&amp;showTz=0&amp;mode=AGENDA&amp;wkst=2&amp;bgcolor=\%23ffffff&amp;src=whitleypump.uk\%40gmail.com&amp;color=\%231B887A&amp;src=g4ob4hs2j5vupghan9aek3qck8\%40group.calendar.google.com&amp;color=\%238C500B&amp;src=ncqc6sa132nddcitprllnd14i4\%40group.calendar.google.com&amp;color=\%235229A3&amp;src=9qdcpuri3ltp8jsuaad426i7lg\%40group.calendar.google.com&amp;color=\%23125A12&amp;src=hf00an8oaomsotr5jkea5p85q0\%40group.calendar.google.com&amp;color=\%23711616&amp;ctz=Europe\%2FLondon\" width=100\% height=1500/]<br><br><strong>You are advised to confirm dates, times and prices with whoever is organising the event.</strong> Although <em>The Whitley Pump</em> takes care to get event details correct, we can take no responsibility for errors, omissions or cancellations whether caused by us or by other parties.",
      "category" : "Art &amp; culture, Museums, Katesgrove ward, Redlands ward, Whitley ward",
      "delay" : tomorrow.getDate() + "-" + monthNames[tomorrow.getMonth()] + "-" + tomorrow.getFullYear() + " 08:00:00"
}
);

};
