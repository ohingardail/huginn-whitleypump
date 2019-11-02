// Library of javascript routines and global variables

var monthNames = [
   'January', 'February', 'March',
   'April', 'May', 'June', 'July',
   'August', 'September', 'October',
   'November', 'December' ];

var dayNames = ['Sunday', 
   'Monday', 'Tuesday', 'Wednesday',
   'Thursday', 'Friday', 'Saturday'];

var cardinalNumbers = ['no', 
   'one', 'two', 'three',
   'four', 'five', 'six', 'seven',
   'eight', 'nine' ];

var today = new Date();
var tomorrow = new Date();
var dayaftertomorrow = new Date();
var nextweek = new Date();
tomorrow.setDate(today.getDate() + 1);
dayaftertomorrow.setDate(today.getDate() + 2);
nextweek.setDate(today.getDate() + 8);

// returns date of next day of week specified
function nextDOW(dayName, excludeToday = true, refDate = new Date()) {
	const dayOfWeek = ["sun","mon","tue","wed","thu","fri","sat"]
                      .indexOf(dayName.slice(0,3).toLowerCase());
	if (dayOfWeek < 0) return;
	newDate = new Date(refDate);
	newDate.setHours(1,0,0,0); // setHours(1) to force correct day in case of UTC/BST issues
	newDate.setDate(newDate.getDate() + !!excludeToday + (dayOfWeek + 7 - newDate.getDay() - !!excludeToday) % 7);
	return newDate;
}

// returns unix date (secs - not ms - since jan 1970)
function getUnixDate(refDate = new Date()) {
	return Math.round(refDate.getTime() / 1000);
}

// returns javascript date (ms - not secs - since jan 1970)
function convertUnixDate(unix_timestamp) {
	return new Date(unix_timestamp * 1000);
}

// converts string to proper case - all words in string
function properCase(str) {
  return str.toLowerCase().replace(/\b\S/g, function(t) { return t.toUpperCase() });
}

// converts string to first letter of string uppercase, rest lower case
function capitalise(str) {
  return str.toLowerCase().replace(/^\S/, function(t) { return t.toUpperCase() });
}

// converts string to first letter of string uppercase, rest unchanged
function sentence(str) {
  return str.replace(/^\S/, function(t) { return t.toUpperCase() });
}

// unique sort an array
function sortUnique(arr) {
    arr = arr.sort()
    var ret = [arr[0]]
    for (var i = 1; i < arr.length; i++) { // start loop at 1 as element 0 can never be a duplicate
        if (arr[i-1] !== arr[i]) {
            ret.push(arr[i])
        }
    }
    return ret;
}

// arbitrary sort function for use in sort() method
// http://jsfiddle.net/gfullam/sq9U7/
var by = function (path, reverse, primer, then) {
    var get = function (obj, path) {
            if (path) {
                path = path.split('.');
                for (var i = 0, len = path.length - 1; i < len; i++) {
                    obj = obj[path[i]];
                };
                return obj[path[len]];
            }
            return obj;
        },
        prime = function (obj) {
            return primer ? primer(get(obj, path)) : get(obj, path);
        };
    
    return function (a, b) {
        var A = prime(a),
            B = prime(b);
        
        return (
            (A < B) ? -1 :
            (A > B) ?  1 :
            (typeof then === 'function') ? then(a, b) : 0
        ) * [1,-1][+!!reverse];
    };
};

// checks if arg is array
function isArray(o) {
  return Object.prototype.toString.call(o) === '[object Array]';
}

// checks if arg is JSON string
function isJsonString(str) {
    try {
        JSON.parse(str);
    } catch (e) {
        return false;
    }
    return true;
}

// checks if arg is object
function isObject(o) {
  return o === Object(o);
}

// returns merged object; uses object1 as base and appends or amends from object 2 (1 level only)
function object_merge(object1, object2){
  if ( object1 != null && object1.length == 0 )
  {
    object1=null
  }
  if ( object2 != null && object2.length == 0 )
  {
    object2=null
  }
  if (object1 == null && object2 == null)
  {
    return null
  }
  if (object1 == null && object2 != null)
  {
    return object2
  }
  if (object1 != null && object2 == null)
  {
    return object1
  }
  
  // create base object as clone of object1
  merged_object=JSON.parse(JSON.stringify(object1))
  //this.log("MERGED_OBJECT_BASE:" + JSON.stringify(merged_object))
  
  // amend or append from object 2 (which may not be an object!)
  if (isObject(object2))
  {
    object2_keys=Object.keys(object2)
    for(var o = 0; o < object2_keys.length; o++) 
    {
      object2_key=object2_keys[o]
      merged_object[object2_key]=object2[object2_key]
      // this.log("MERGED_OBJECT[" + object2_key + "]:" + JSON.stringify(object2[object2_key]))
    }
  } else if (isArray(object2)) {
     merged_object=object2
  } else {
    // deal with case when munged credential object by this point is no longer an object '{"X":"Y"}', but just "Y"
    merged_object['value']=object2
  }
    
  return merged_object
}

// returns random integer from min (inclusive) upto max-1 (ie exclusive of max)
function randomint(min, max) {
 return Math.floor(Math.random() * (max - min + 1) ) + min;
}

// returns json object from (cleaned) event.body returned by wp rest api
function parseResponse(event)
{
  // find body
  var newBody = ''
  if ('body' in event )
  {
	newBody =  event.body
  }
  else if ('payload' in event && 'body' in event.payload )
  {
	newBody =  event.payload.body
  }

  // if there's anything to do...
  if ( newBody.length > 0)
  {
   newBody = newBody.replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/\t/g, "\\t").replace(/\f/g, "\\f")
   newBody = newBody.replace(/\\(^\\)+/g, '$1')
   newBody = newBody.replace(/\\(\\)+/g, '$1')
  
   //this.log(cleaned_body);
    return JSON.parse(newBody);
    
  } else {
    
    return null;
    
  }    
}

// extracts values from SG endpoints stored as a credential
function getEndpoint(endpoint, key, value, field) {
	var endpoint_obj = JSON.parse(Agent.credential(endpoint))
	// Agent.log(endpoint_obj)
  for (var i = 0; i < endpoint_obj.length; i++) 
  {
    // Agent.log(endpoint_obj[i])
    if (endpoint_obj[i][key] === value) 
    {
      return endpoint_obj[i][field];
    }
  }
  return null;
}

// basic string cleaner, good for all cases
function basic_clean(string){

    	// replace nonstandard apostrophes
  	//string = string.replace(/[\x93\x94]+/gi, '"')
  	string = string.replace(/[\u0093\u0094\u201C\u201D]+/gi, '"')

  	//string = string.replace(/[\x91\x92]+/gi, "'")
  	string = string.replace(/[\u0091\u0092\u2018\u2019\u201B\u02BC\uFF07\u07F4\u07F5]+/gi, "'")

  	// replace non-standard hyphens
  	string = string.replace(/\s*[\u2013\u2014\u2E3A\u2E3B\uFE58\uFE63\uFF0D]\s*/gi, ' - ')

	// replace ellipsis char with '...'
  	string = string.replace(/(\s*\u2026\s*)+/gi, '... ')

  	// replace non-standard full stops
  	string = string.replace(/\s*[\u0701\u0702\u2E3C\uFE52\uFF0E]+\s*/gi, '. ')

  	// clean out nonprinting chars except NL, CR, TAB
  	string = string.replace(/[^\x09\x0A\x0D\x20-\x7E\x80-\xFF]+/gi, '')

  	// replace ’S with 's
  	string = string.replace(/\'S\s*/gi, "'s ")

  	// replace duplicate spaces
  	string = string.replace(/[\xA0\x09\x20]+/gi, ' ')
  
  	return string;
}

// clean post title text
function clean_title(string) {
  	string = basic_clean(string)

  	// removes newlines, tabs
  	string = string.replace(/[\x09\x0A\x0D]+/gi, '') 

  	// removes HTML
  	string = string.replace(/<.*?>/gi, '') 
  
  	// replace 'and' html entity
  	string = string.replace(/&amp;/gi, 'and')

  	// replace 'nonbreaking space' html entity
  	string = string.replace(/&nbsp;/gi, ' ')

  	return string;
}

// clean post content text
function clean_content(string) {
	string = basic_clean(string)
  
	// replace doubled-up quotes unless preceded with '='
	string = string.replace(/(?<!=)([\'\"])+/gi, '$1')
  
	// remove redundant div tags
	string = string.replace(/\<div\>([^]*?)\<\/div\>/gi,'$1')
	string = string.replace(/\<div\s+(?:id|lang|class)=".*?"\s*\>(.*?)\<\/div\>/gi,'$1')
	// remove redundant span tags
	string = string.replace(/\<span\>([^]*?)\<\/span\>/gi,'$1')
	string = string.replace(/\<span\s+(?:id|lang|class|style)=".*?"\s*\>(.*?)\<\/span\>/gi,'$1')
	// remove redundant p tags
	string = string.replace(/\<p\>([^]*?)\<\/p\>/gi,'$1')
	string = string.replace(/\<p\s+(?:id|lang|class)=".*?"\s*\>(.*?)\<\/p\>/gi,'$1')
	// remove redundant <br id> tags
	string = string.replace(/\<br\s+id=".*?"\s*\/\>\s+/gi,'\n')
  
	// make ellipses standard
	string = string.replace(/(\w+)\.{2,}\s*(\w+)/gi,'$1... $2')
	//string = string.replace(/(\.+\s+)?\.{2,}(\s*\.+)?/gi,'... ')
  
	// remove duplicated punctuation
	string = string.replace(/(&amp;){2,}/gi, '$1')
	string = string.replace(/([\(\)]){2,}/gi, '$1')
	string = string.replace(/([!?,:;$]){2,}/gi, '$1')
	string = string.replace(/[!?,:;]\./gi, '.',)
	string = string.replace(/'\.([!?,:;])/gi, '$1')
  
  	// make sure "xxx ," doesnt happen
	string = string.replace(/\b(\w+)\s+,\s?/gi, '$1, ')

	// standardise double lines and remove spaces before newlines
	string = string.replace(/\s*\n+/gi, '\n\n')

	// headify links header
	string = string.replace(/\n+(\<hr\s*\/\>\n+)*(\<h\d\>\s*)?Links(\<\/h\d\>\s*)?\n+/i, '<hr />\n<h5>Links</h5>\n')
	//string = string.replace(/\<hr\s?\/?\s?\>\n+Links\s?\n+/i, '<hr />\n<h5>Links</h5>\n')

	// remove initial blank line (this can remove *all* blank lines)
	string = string.replace(/^(?:\s|\n)*([^]*)/i, '$1')
	
	// correctly form initial byline (if any)
	string = string.replace(/^(?:\<em\>)?\s*(By\\b.*?)[\.\s]*(?:\<\/em>)?\n/gi, '<em>$1.</em>\n')	
	
	// remove terminal blank lines
	string = string.replace(/(.*)(?:\s|\n)*$/i, '$1')

	// PICS

	// make pic full size
	// buggers up [caption ... width...]
	//string = string.replace(
	//	/\<img\s+(.*)?width="\d+?"\s+height="\d+?"\s+\>/gi,
	//	'<img $1 width="100%" height="100%" />')

	// ensure all pics open correct page 
	// fix pics with no link
	string = string.replace(
		/\<img class="(.*?(\d+).*?)"[\b\s]*src="(.*?)"(.*?)[\b\s]*\/\>/gi,
		'<a href="https://whitleypump.net/?attachment_id=$2" target="_blank" rel="noopener noreferrer"><img class="$1" src="$3" $4 /></a>')
  
  	// fixed duplicated hrefs (where post has mix of linked and unlinked pics)
	string = string.replace(
		/(\<a\s+.*?\>)(\<a\s+.*?\>)(\<img\s+.*?\/\>)(\<\/a\>)+/gi,
		'$2$3</a>')
		
  	// fix pics with 'custom link'
	string = string.replace(
		/\<a href="(whitleypump\.net(?:(?!attachment_id).)*)"\>[\b\s]*\<img class="(.*?(\d+).*?)"[\b\s]*src="(.*?)"(.*?)[\b\s]*\/>[\b\s]*\<\/a\>/gi,
		'<a href="https://whitleypump.net/?attachment_id=$3" target="_blank" rel="noopener"><img class="$2" src="$4" $5 /></a>')

	// LINKS 

	// ensure all links open in new page
	string = string.replace(/\<a\s+(.*?)\>/gi, '<a $1 target="_blank" rel="noopener noreferrer">')
	string = string.replace(/(\btarget="_blank"\s+rel="(noopener|\s|noreferrer)+"\s*)+/gi, '$1')
  
  	// ensure all internal links (aka bookmarks with href="#abc") *dont* open in new page
	

	// MORE LINE
	
	// add more line after first para, if one not already included
	if (string.search(/\<!--more--\>/i) < 0 )
	{
	  //string = string.replace(/^(\<a[^\n]+\<\/a\>\n+[^\n]+)\n*/i, '$1\n\n<!--more-->\n')
	  string = string.replace(
	    /^((?:[\[\<].*?[\]\>]\n+)?[^\n]*?)\n+/i,
	   '$1\n\n<!--more-->'
	  )
	}
	// make sure more line is correctly spaced
	//string = string.replace(/(?:(\<br\s?\/?\s?\>|\n))*<(?:!-*)?more(?:-*)?\>(?:(\<br\s?\/?\s?\>|\n))*/i, '\n\n<!--more-->')
	string = string.replace(/[\n\s]*\<!-*more-*\>[\n\s]*/i, '\n\n<!--more-->')
	
  	return string;
}

// returns csv string of categories ids whose names are found in given string
// uniqued, with 'uncategorized' removed
// input parm 'categories' is stringified array of category ids already in the post
function categorise(string, categories)
{
	var categoryList = []

	// initialise output list with input list (if there is one)
	if ( categories.length > 0 )
	{
		categoryList.push.apply(categoryList, JSON.parse("[" + categories.replace(/[^0-9,]/gi, '') + "]"))
		Agent.log("categoryList=" + JSON.stringify(categoryList) )
	}

	// if there's anything to do...
	if ( string.trim().length > 0 )
	{
		// get list of all categories in system
		var allCategories = JSON.parse(Agent.credential('wpsg_categories'))
		//Agent.log("allCategories=" + JSON.stringify(allCategories))

		// identify categories that appear in the string
	 	for (var i = 0; i < allCategories.length; i++) 
		{
			//Agent.log("allCategories[i]['name'].trim().toUpperCase()=" + allCategories[i]['name'].trim().toUpperCase() )
			// remove 'uncategorized' category
			if ( allCategories[i]['name'].trim().toUpperCase() == 'UNCATEGORIZED' )
			{
				//Agent.log("allCategories[i]['name'].trim().toUpperCase()=" + allCategories[i]['name'].trim().toUpperCase() )
				var uncategorizedIdIndex = categoryList.indexOf(allCategories[i]['id']);
				// Agent.log("uncategorizedIdIndex=" + uncategorizedIdIndex )
				if ( uncategorizedIdIndex >= 0 && categoryList.length > 1)
				{
					categoryList.splice(uncategorizedIdIndex, 1);
				}
			} else {
				var categoryName = "\\b" + allCategories[i]['name'].trim().replace(/&amp;/gi, 'and').replace(/\s+/g, '\\s+') + "\\b"
				
				var regex = new RegExp( categoryName ,"ig");

				if (string.search(regex) >= 0 ) 
				{
					categoryList.push(allCategories[i]['id'])
		       		}
			}
		}

		// unique list 
		outputCategoryList = JSON.stringify(sortUnique(categoryList)).replace(/[\[\]]/g, '')
	}

	//Agent.log("outputCategoryList=" + outputCategoryList)
	return outputCategoryList
}

// returns id of specified tag or cat
function get_taxonomy(taxonomy, string)
{
  
  if (taxonomy.length > 0 && string.length > 0 )
  {
    if (taxonomy.toUpperCase() == 'TAG')
    {
      var taxon = 'wpsg_tags'
    } else if (taxonomy.toUpperCase() == 'CATEGORY')
    {
      var taxon = 'wpsg_categories'
    }
    
    var all = JSON.parse(Agent.credential(taxon))
  
    if (all.length > 0 )
    {
      for (var i = 0; i < all.length; i++) 
	    {
	      if ( all[i]['name'].trim().toUpperCase() == string.toUpperCase() )
	      {
	        return all[i]['id']
		      break
    	  }
      }
    }
  }
}
