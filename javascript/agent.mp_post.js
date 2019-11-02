{% credential javascript_library %}

Agent.receive = function() {

	var incomingEvents = this.incomingEvents();
  
	// for each incoming event (usually just one giant event)
	for(var i = 0; i < incomingEvents.length; i++)
	{
		mpItems = incomingEvents[i].payload.events.sort(
								by(	'recordType', 
									false, 
									function (x) {return x.toUpperCase().replace(/\W/g, '');},
									by(	'recordUnixDate', 
										false, 
										parseInt,
										by(	'divisionNumber',
											false, 
											function (x) {return x || '0' ;},
											by(	'recordId',
												false, 
												function (x) {return x.toUpperCase().replace(/\W/g, '');}
											)
										)
									) 
								)
							);
    
		//this.log("mpItems=" + JSON.stringify(mpItems) );

		// initialise record    
		var mpObject = {};
		var wardList = [];
		var linkList = [];
		var titleString = '';
		var introString = '';
		var introStringList = [];
		var imageString = '';
		var old_mpTwfuContribTitle = '';
		var old_mpFullName = '';
		var print = false;
		var earliestDate = new Date; 
		//var credential = {};	    

		var divisionObject = {};
		var divisionString = '';
		var divisionList = {};
	
		var edmObject = {};
		var edmString = ''; 
		var edmList = {};

		var debateString = '';
		var debateList = {};		

		var writtenQAList = {};
		var writtenQAstring = '';

		var oralQAstring = '';
		var oralQAList = {};

		var unknownString = '';

		// for each record in giant event
		for(var n = 0; n < mpItems.length; n++)
		{
			mpItem = mpItems[n];
			wardList = wardList.concat(mpItem.ward.split(','));
			// this.log("wardList=" + JSON.stringify(wardList));
	      
			recordDate = new Date(mpItem.recordUnixDate * 1000);
			recordDateString = recordDate.getDate() + " " + monthNames[recordDate.getMonth()];
			if (recordDate < earliestDate )
			{
				earliestDate = recordDate;
			}

			// assemble mp list
			if (!mpObject[mpItem.mpFullName])
			{
       				mpObject[mpItem.mpFullName] = {};
			}
			mpObject[mpItem.mpFullName]['party'] = mpItem.mpParty;
			mpObject[mpItem.mpFullName]['constituency'] = mpItem.constituency;
			if (mpItem.mpHomePage && mpItem.mpHomePage.length > 0 )
			{
				mpObject[mpItem.mpFullName]['homepage'] = encodeURI(mpItem.mpHomePage);
			}

			// set personal pronoun
			mpObject[mpItem.mpFullName]['subject_pronoun'] = 'they'
			mpObject[mpItem.mpFullName]['object_pronoun'] = 'them'
			mpObject[mpItem.mpFullName]['possessive_pronoun'] = 'their'
			if ( mpItem.mpGender.toLowerCase().trim() == 'male' )
			{
				mpObject[mpItem.mpFullName]['subject_pronoun'] = 'he'
				mpObject[mpItem.mpFullName]['object_pronoun'] = 'him'
				mpObject[mpItem.mpFullName]['possessive_pronoun'] = 'his'
			} else if ( mpItem.mpGender.toLowerCase().trim() == 'female' )
			{
				mpObject[mpItem.mpFullName]['subject_pronoun'] = 'she'
				mpObject[mpItem.mpFullName]['object_pronoun'] = 'her'
				mpObject[mpItem.mpFullName]['possessive_pronoun'] = 'her'
			}
	
			// rodda's homepage not yet on hansard api
			if (mpItem.mpFullName == 'Matt Rodda' && mpItem.mpHomePage.length == 0 )
			{
				mpObject[mpItem.mpFullName]['homepage'] = 'https://www.mattrodda.net/';
			}

			if (mpItem.mpTwitter && mpItem.mpTwitter.length > 0 )
			{
				mpObject[mpItem.mpFullName]['twitter'] = encodeURI(mpItem.mpTwitter);
			}
			if (mpItem.mpTwfuOffice && mpItem.mpTwfuOffice.length > 0 )
			{
				mpObject[mpItem.mpFullName]['office'] = mpItem.mpTwfuOffice;
			}
			if (mpItem.mpTwfuUrl && mpItem.mpTwfuUrl.length > 0 )
			{
				mpObject[mpItem.mpFullName]['twfuurl'] = encodeURI(mpItem.mpTwfuUrl);
			}
			if (mpItem.mpHansardUrl && mpItem.mpHansardUrl.length > 0 )
			{
				mpObject[mpItem.mpFullName]['hansardurl'] = encodeURI(mpItem.mpHansardUrl);
			}

			// initialise 
			if (!writtenQAList[mpItem.mpFullName])
			{
       				writtenQAList[mpItem.mpFullName] = {"r":0, "q":0};
			}
			if (!oralQAList[mpItem.mpFullName])
			{
       				oralQAList[mpItem.mpFullName] = {"r":0, "q":0};
			}
			if (!debateList[mpItem.mpFullName])
			{
				debateList[mpItem.mpFullName] = [];
			}
			if (!divisionList[mpItem.mpFullName])
			{
       				divisionList[mpItem.mpFullName] = [];
			}

			// make sure URLs are encoded
			if (mpItem.mpTwfuOtherSpeakerUrl && mpItem.mpTwfuOtherSpeakerUrl.length > 0 )
			{
				mpItem.mpTwfuOtherSpeakerUrl = encodeURI(mpItem.mpTwfuOtherSpeakerUrl);
			}	
			if (mpItem.mpTwfuContribUrl && mpItem.mpTwfuContribUrl.length > 0 )
			{
				mpItem.mpTwfuContribUrl = encodeURI(mpItem.mpTwfuContribUrl);
			}	


			//if (!credential[mpItem.constituency])
			//{
       			//	credential[mpItem.constituency] = {};
			//}

			// process each record type
			switch(mpItem.recordType.toLowerCase().trim()) 
			{
			//case 'written-questions': // OLD 'They Work For You' interface
			//	switch (mpItem.mpTwfuContribTypeQR.trim())
			//	{
			//		case 'r':
			//			writtenQAstring += '<a href=' + mpItem.mpTwfuOtherSpeakerUrl + ' target=_blank>' + mpItem.mpTwfuOtherSpeaker + '</a> (' + mpItem.mpTwfuOtherSpeakerPosition + ') wrote to ' + mpItem.mpFullName + ' to ask a question on ' + recordDateString + ':';
			//			writtenQAstring += '<blockquote>' + mpItem.mpTwfuOtherSpeakerText + '</blockquote>';
			//			writtenQAstring += mpItem.mpFullName + '<a href=' + mpItem.mpTwfuContribUrl + ' target=_blank> responded</a>: ';
			//			writtenQAstring += '<blockquote>' + mpItem.mpTwfuContribText + '</blockquote>';
			//			writtenQAList[mpItem.mpFullName]['r'] += 1;
			//		break;
			//		case 'q':
			//			writtenQAstring += mpItem.mpFullName + ' wrote to <a href=' + mpItem.mpTwfuOtherSpeakerUrl + ' target=_blank>' + mpItem.mpTwfuOtherSpeaker + '</a> (' + mpItem.mpTwfuOtherSpeakerPosition + ') to ask a <a href=' + mpItem.mpTwfuContribUrl + ' target=_blank> question</a> on ' + recordDateString + ':';
			//			writtenQAstring += '<blockquote>' + mpItem.mpTwfuContribText + '</blockquote>';
			//			writtenQAstring += mpItem.mpTwfuOtherSpeaker + '<a href=' + mpItem.mpTwfuContribUrl + ' target=_blank> responded</a>: ';
			//			writtenQAstring += '<blockquote>' + mpItem.mpTwfuOtherSpeakerText + '</blockquote>';
			//			writtenQAList[mpItem.mpFullName]['q'] += 1;
			//		break;
			//	}
			//	print = true;
			//break;

			case 'written-answers':
			case 'written-answer':
			case 'written-questions':
			case 'written-question':
			
				if (mpItem.mpFullName == mpItem.qaTablingMemberPrinted)
				{
					writtenQAstring += mpItem.qaTablingMemberPrinted + 
							' wrote to <a href=' + mpItem.mpTwfuOtherSpeakerUrl + ' target=_blank rel="noopener noreferrer">' + 
							mpItem.qaAnsweringMemberPrinted + '</a> (' + 
							mpItem.mpTwfuOtherSpeakerPosition + ') ';
				} else
				{
					writtenQAstring += '<a href=' + mpItem.mpTwfuOtherSpeakerUrl + ' target=_blank rel="noopener noreferrer">' + 
							mpItem.qaTablingMemberPrinted + '</a> (' + 
							mpItem.mpTwfuOtherSpeakerPosition + ') wrote to ' + 
							mpItem.qaAnsweringMemberPrinted ;
				}
				writtenQAstring += ' to ask a question' + 
						( mpItem.qaDateOfQuestion ? ' on ' + mpItem.qaDateOfQuestion.split('-')[2].replace(/^0+/, '') + ' ' + monthNames[mpItem.qaDateOfQuestion.split('-')[1] - 1] : '') + ':';
				writtenQAstring += '<blockquote>' + mpItem.qaQuestionText + '</blockquote>';
				writtenQAstring += mpItem.qaAnsweringMemberPrinted + ' responded' + 
						( mpItem.qaDateOfAnswer ? ' on ' + mpItem.qaDateOfAnswer.split('-')[2].replace(/^0+/, '') + " " + monthNames[mpItem.qaDateOfAnswer.split('-')[1] - 1] : '')  + ':';
				writtenQAstring += '<blockquote>' + mpItem.qaAnswerText + '</blockquote>';
				writtenQAList[mpItem.mpFullName][(mpItem.mpFullName ==  mpItem.qaTablingMemberPrinted ? 'q' : 'r')] += 1;
				print = true;

			break;

			case 'oral-answers':
			case 'oral-answer':
			case 'oral-questions':
			case 'oral-question':
				
				if (mpItem.mpFullName == mpItem.qaTablingMemberPrinted)
				{
					oralQAstring +=	mpItem.qaTablingMemberPrinted + ' asked <a href=' + mpItem.mpTwfuOtherSpeakerUrl + ' target=_blank rel="noopener noreferrer">' + mpItem.qaAnsweringMemberPrinted + '</a> (' + mpItem.mpTwfuOtherSpeakerPosition + ') ';
				} else
				{
					oralQAstring +=	'<a href=' + mpItem.mpTwfuOtherSpeakerUrl + ' target=_blank rel="noopener noreferrer">' + mpItem.qaTablingMemberPrinted + '</a> (' + mpItem.mpTwfuOtherSpeakerPosition + ') asked ' + mpItem.qaAnsweringMemberPrinted ;
				}
				oralQAstring += ' a question' + 
						( mpItem.qaDateOfQuestion ? ' on ' + mpItem.qaDateOfQuestion.split('-')[2].replace(/^0+/, '') + ' ' + monthNames[mpItem.qaDateOfQuestion.split('-')[1] - 1] : '') + ':';
				oralQAstring += '<blockquote>' + mpItem.qaQuestionText + '</blockquote>';
				oralQAstring += mpItem.qaAnsweringMemberPrinted + ' responded' + 
						( mpItem.qaDateOfAnswer ? ' on ' + mpItem.qaDateOfAnswer.split('-')[2].replace(/^0+/, '') + " " + monthNames[mpItem.qaDateOfAnswer.split('-')[1] - 1] : '')  + ':';
				oralQAstring += '<blockquote>' + mpItem.qaAnswerText + '</blockquote>';
				oralQAList[mpItem.mpFullName][(mpItem.mpFullName ==  mpItem.qaTablingMemberPrinted ? 'q' : 'r')] += 1;
				print = true;

			break;
			case 'commons-debate':
			case 'commons-debates':

				// this.log("old_mpTwfuContribTitle=" + old_mpTwfuContribTitle);
				// this.log("mpItem.mpTwfuContribTitle=" + mpItem.mpTwfuContribTitle);
				// this.log("old_mpFullName=" + old_mpFullName);
				// this.log("mpItem.mpFullName=" + mpItem.mpFullName);
				if ( old_mpTwfuContribTitle.length == 0 || old_mpTwfuContribTitle != mpItem.mpTwfuContribTitle || old_mpFullName.length == 0 || old_mpFullName != mpItem.mpFullName ) 
				{
					debateString += 'In the <a href=https://hansard.parliament.uk/Commons/ target=_blank rel="noopener noreferrer">House of Commons</a> on ' 
						+ recordDateString + ', ' 
						+ mpItem.mpFullName 
						+ ' spoke in the <a href=' 
						+ mpItem.mpTwfuContribUrl 
						+ ' target=_blank>' 
						+  mpItem.mpTwfuContribTitle 
						+ '</a> debate:';

					old_mpTwfuContribTitle = mpItem.mpTwfuContribTitle;
					old_mpFullName = mpItem.mpFullName;

					debateList[mpItem.mpFullName].push('<a href=' + mpItem.mpTwfuContribUrl.split('#')[0] + '  target=_blank rel="noopener noreferrer">' + mpItem.mpTwfuContribTitle.split('-')[0].replace(/\bbill\b/ig, '').replace(/\s+/g, ' ').trim() + '</a>');

					//this.log("debateList[mpItem.mpFullName])=" + JSON.stringify(debateList[mpItem.mpFullName]));
				}

				debateString += '<blockquote>' 
					+ mpItem.mpTwfuContribText 
					+ '<p style="text-align: right;"><em><a href=' 
					+ mpItem.mpTwfuContribUrl 
					+ '  target=_blank rel="noopener noreferrer">[see context]</a></em></p></blockquote>';
				print = true;
			break;
			case 'westminster-hall-debate':
			case 'westminster-hall-debates':

				if ( old_mpTwfuContribTitle.length == 0 || old_mpTwfuContribTitle != mpItem.mpTwfuContribTitle || old_mpFullName.length == 0 || old_mpFullName != mpItem.mpFullName ) 
				{
	 				debateString += 'In Westminster Hall on ' 
						+ recordDateString 
						+  ', ' 
						+ mpItem.mpFullName 
						+ ' spoke in the <a href=' 
						+ mpItem.mpTwfuContribUrl
						+ ' target=_blank rel="noopener noreferrer">' 
						+  mpItem.mpTwfuContribTitle 
						+ '</a> debate:';
					old_mpTwfuContribTitle = mpItem.mpTwfuContribTitle;
					old_mpFullName = mpItem.mpFullName;

					debateList[mpItem.mpFullName].push('<a href=' + mpItem.mpTwfuContribUrl.split('#')[0] + ' target=_blank rel="noopener noreferrer">' + mpItem.mpTwfuContribTitle.split('-')[0].replace(/\bbill\b/ig, '').replace(/\s+/g, ' ').trim() + '</a>');
				}

				debateString += '<blockquote>' 
					+ mpItem.mpTwfuContribText 
					+ '<p style="text-align: right;"><em><a href=' 
					+ mpItem.mpTwfuContribUrl 
					+ ' target=_blank rel="noopener noreferrer">[see context]</a></em></p></blockquote>';
				print = true;
			break;
			case 'division':
			case 'divisions':

				if (!divisionObject[mpItem.divisionTitle])
				{
        				divisionObject[mpItem.divisionTitle] = {};
				}
				if (!divisionObject[mpItem.divisionTitle][mpItem.mpFullName] )
				{
					divisionObject[mpItem.divisionTitle][mpItem.mpFullName] = {};
				}

				divisionObject[mpItem.divisionTitle][mpItem.mpFullName]['divisionType'] = ( mpItem.divisionType ? mpItem.divisionType : '' );
				divisionObject[mpItem.divisionTitle][mpItem.mpFullName]['hansardId'] = mpItem.mpHansardId;


				divisionObject[mpItem.divisionTitle]['divisionSearch'] = encodeURI('https://hansard.parliament.uk/search?house=Commons&partial=False&searchTerm=' + mpItem.divisionTitle.split(':')[0].replace(/^draft\s+/i, '').replace(/\s+/g, ' ').trim() + '&startDate=' + mpItem.divisionDate + '&endDate=' + mpItem.divisionDate);
				divisionObject[mpItem.divisionTitle]['divisionDate'] = mpItem.divisionDate;
				divisionObject[mpItem.divisionTitle]['divisionDateString'] = recordDateString;
				divisionObject[mpItem.divisionTitle]['divisionNumber'] = mpItem.divisionNumber;
				divisionObject[mpItem.divisionTitle]['divisionAyesCount'] = ( mpItem.divisionAyesCount ? mpItem.divisionAyesCount : '0' );
				divisionObject[mpItem.divisionTitle]['divisionNoesCount'] = ( mpItem.divisionNoesCount ? mpItem.divisionNoesCount : '0' );
				
				divisionObject[mpItem.divisionTitle]['result'] = (( parseInt(divisionObject[mpItem.divisionTitle]['divisionAyesCount']) > parseInt(divisionObject[mpItem.divisionTitle]['divisionNoesCount']) ) ? 'aye' : 'no');

				divisionList[mpItem.mpFullName].push('<a href=' + divisionObject[mpItem.divisionTitle]['divisionSearch'] + ' target=_blank rel="noopener noreferrer">' + mpItem.divisionTitle.split(':')[0].replace(/^draft\s+/i, '').replace(/\s+/g, ' ').trim() + '</a>');
				print = true;
				//this.log("divisionObject=" + JSON.stringify(divisionObject)); 
			break;
			case 'early-day-motion':
			case 'early-day-motions':

				if (!edmList[mpItem.mpFullName])
				{
	       				edmList[mpItem.mpFullName] = {};
					edmList[mpItem.mpFullName]['sponsored'] = 0;
					edmList[mpItem.mpFullName]['supported'] = 0;
				}

				if (!edmObject[mpItem.edmTitle])
				{
        				edmObject[mpItem.edmTitle] = {};
				}
				edmObject[mpItem.edmTitle][mpItem.mpFullName] = mpItem.edmType;
				edmObject[mpItem.edmTitle]['edmDateTabled'] = mpItem.edmDateTabled;
				edmObject[mpItem.edmTitle]['edmDateString'] = recordDateString;
				edmObject[mpItem.edmTitle]['edmNumber'] = mpItem.edmNumber;
				edmObject[mpItem.edmTitle]['edmSession'] = mpItem.edmSession;
				edmObject[mpItem.edmTitle]['edmPrimarySponsor'] = mpItem.edmPrimarySponsor;
				edmObject[mpItem.edmTitle]['edmNumberOfSignatures'] = mpItem.edmNumberOfSignatures;
				edmObject[mpItem.edmTitle]['edmStatus'] = mpItem.edmStatus;

				edmList[mpItem.mpFullName][mpItem.edmType] += 1;
				print = true;
			break;
			default:
				unknownString += JSON.stringify(mpItem);
			} //switch
	      
		} //for(var n = 0; n < mpItems.length; n++)

		//this.log("divisionObject=" + JSON.stringify(divisionObject)); 
	    
		// if there is anything worth printing...
		if ( print )
		{
			var mpObjectKeys=Object.keys(mpObject)

			// assemble sections
			if ( writtenQAstring.length > 0)
			{
				writtenQAstring = '<h5>Written questions</h5>' +
						'MPs (or peers from the House of Lords) can submit <a href=https://www.parliament.uk/about/how/business/written-answers/ target=_blank rel="noopener noreferrer">written questions</a> to government ministers.<br><br>'
						+ writtenQAstring;
			}
			if ( oralQAstring.length > 0)
			{
				oralQAstring = '<h5>Oral questions</h5>' +
						'MPs can ask <a href=https://www.parliament.uk/about/how/business/urgent-question/ target=_blank rel="noopener noreferrer">oral or urgent questions</a> to government ministers.<br><br>'
						+ oralQAstring;
			}
			if ( debateString.length > 0)
			{
				debateString = '<h5>Commons debates</h5>' +
						'MPs discuss proposals during <a href=https://www.parliament.uk/about/how/business/debates/ target=_blank rel="noopener noreferrer">commons debates.</a> These usually take place in the House of Commons, but can also occur in Westminster Hall.<br><br>'
						+ debateString;
			}
			
			// if there are any divisions logged...
			if ( Object.keys(divisionObject).length > 0)
			{
				divisionString = '<h5>Commons divisions</h5>';
				divisionString += 'A <a href=https://www.parliament.uk/about/how/business/divisions/ target=_blank rel="noopener noreferrer">division</a> is a vote. MPs may vote many times in any one debate, and you may need to examine the context of each vote to work out what it was about.';
				divisionString += '<table><tr><th>Bill and division</th><th style="text-align:center;">'
						+ mpObjectKeys.join('</th><th style="text-align:center;">')
						+ '</th><th style="text-align:center;vertical-align:top;">Ayes</th><th style="text-align:center;vertical-align:middle;">Noes</th><th style="text-align:center;vertical-align:bottom;">Result</th></tr>';

				//this.log("divisionObject=" + JSON.stringify(divisionObject));
				//this.log("divisionObjectKeys=" + JSON.stringify(divisionObjectKeys)); 

				var divisionObjectKeys=Object.keys(divisionObject)
				for (var d = 0; d < divisionObjectKeys.length; d++)
				{

					// this.log("divisionObjectKeys[d]=" + JSON.stringify(divisionObjectKeys[d])); 

					divisionString += '<tr><td>' + 
						'<a href=' + divisionObject[divisionObjectKeys[d]]['divisionSearch'] + ' target=_blank rel="noopener noreferrer">' +
						sentence(divisionObjectKeys[d]).replace(':', '<br>') + '</a>' +
						'<br>' + 
						'Division ' + 
						divisionObject[divisionObjectKeys[d]]['divisionNumber'] + ', ' + 
						divisionObject[divisionObjectKeys[d]]['divisionDateString'] + '</td>';

					for(var m = 0; m < mpObjectKeys.length; m++)
					{
						// this.log("mpObjectKeys[m]=" + JSON.stringify(mpObjectKeys[m]));
						// this.log("divisionObject[divisionObjectKeys[d]]=" + JSON.stringify( divisionObject[divisionObjectKeys[d]])); 
						// this.log("divisionObject[divisionObjectKeys[d]][mpObjectKeys[m]]=" + JSON.stringify( divisionObject[divisionObjectKeys[d]][mpObjectKeys[m]])); 
	
						mpVote = '';
						if ( divisionObject[divisionObjectKeys[d]][mpObjectKeys[m]] )
						{
							mpVote = ( divisionObject[divisionObjectKeys[d]][mpObjectKeys[m]]['divisionType'] ? divisionObject[divisionObjectKeys[d]][mpObjectKeys[m]]['divisionType'] : '' );
						}

						if (mpVote.length > 0 )
						{
							divisionString += '<td style="text-align:center;vertical-align:middle;">' + 
								(mpVote == divisionObject[divisionObjectKeys[d]]['result'] ? '<strong>' : '') + 
								'<a href=' +
								encodeURI('https://hansard.parliament.uk/search/MemberContributions?type=Divisions&memberId=' +
									divisionObject[divisionObjectKeys[d]][mpObjectKeys[m]]['hansardId'] + 
									'&startDate=' + divisionObject[divisionObjectKeys[d]]['divisionDate'] + 
									'&endDate=' + divisionObject[divisionObjectKeys[d]]['divisionDate'])
								+ ' target=_blank>'+
								mpVote + '</a>' +
								(mpVote == divisionObject[divisionObjectKeys[d]]['result'] ? '</strong>' : '') + '</td>';
						} else {
							divisionString += '<td></td>';
						}
					}

					divisionString += '<td style="text-align:center;vertical-align:middle;">' + divisionObject[divisionObjectKeys[d]]['divisionAyesCount'] + '</td>' 
							+ '<td style="text-align:center;vertical-align:middle;">' + divisionObject[divisionObjectKeys[d]]['divisionNoesCount'] + '</td>' 
							+ '<td style="text-align:center;vertical-align:middle;"><strong>' + divisionObject[divisionObjectKeys[d]]['result'] + '</strong></td></tr>';
				}
				divisionString += '</table>';
			}

			var edmObjectKeys=Object.keys(edmObject)
			if ( edmObjectKeys.length > 0)
			{
				mpEdmList = Object.keys(edmList);
				edmString = '<h5>Early day motions</h5>';
				edmString += 'An <a href=https://www.parliament.uk/about/how/business/edms/ target=_blank rel="noopener noreferrer">early day motion</a> (EDM) is a motion submitted for debate for which no time has been allocated. Consequently very few are actually debated; they are vehicles for MPs to highlight issues they consider important. By convention, government ministers do not submit EDMs. EDMs are sponsored by one or more MPs and can be supported (signed) by others.'

				edmString += '<table><tr><th>EDM title</th><th>Primary sponsor</th><th>' + mpEdmList.join('</th><th >') + '</th><th style="text-align:center;vertical-align:middle">Number of signatures</th></tr>';

				for (var e = 0; e < edmObjectKeys.length; e++)
				{
					edmString += '<tr><td>' +
						( edmObject[edmObjectKeys[e]]['edmSession'] && edmObject[edmObjectKeys[e]]['edmNumber'] ? 
							'<a href=' +
								encodeURI('https://www.parliament.uk/edm/' 
									+ edmObject[edmObjectKeys[e]]['edmSession'].replace('/', '-') +'/' 
									+ edmObject[edmObjectKeys[e]]['edmNumber']
								)
								+ ' target=_blank rel="noopener noreferrer">'
								+ properCase(edmObjectKeys[e])
								+ '</a><br>'
							: properCase(edmObjectKeys[e]) + '<br>' )
						+ '(EDM ' + edmObject[edmObjectKeys[e]]['edmNumber'] + ')</td><td>'
						+ edmObject[edmObjectKeys[e]]['edmPrimarySponsor'] + '</td>';

					for(var l = 0; l < mpEdmList.length; l++)
					{
						edmString += '<td style="text-align:center;vertical-align:middle">' + ( edmObject[edmObjectKeys[e]][mpEdmList[l]] ? edmObject[edmObjectKeys[e]][mpEdmList[l]] : '' ) + '</td>';
					}
					edmString += '<td style="text-align:center;vertical-align:middle;">' + edmObject[edmObjectKeys[e]]['edmNumberOfSignatures'] + '</td></tr>';
				}

				edmString += '</table>';
			}

			// assemble final strings and links
			if ( mpObjectKeys.length > 0)
			{
				for (var m = 0; m < mpObjectKeys.length; m++)
				{

					// assemble list of links
					mpLinkString = '';
					if (mpObject[mpObjectKeys[m]]['homepage'] && mpObject[mpObjectKeys[m]]['homepage'].length > 0 )
					{
						mpLinkString += ' <a href=' + 
							mpObject[mpObjectKeys[m]]['homepage'] + 
							' target=_blank rel="noopener noreferrer">home page</a>,';
					// } else 
					// {
					//	mpLinkString += ' <a href=https://www.google.com/search?q=' + 
					//		mpObjectKeys[m].replace(/\s+/g, '+') + 
					//		' target=_blank>Google search</a>, ';
					}
					if (mpObject[mpObjectKeys[m]]['twitter'] && mpObject[mpObjectKeys[m]]['twitter'].length > 0 )
					{
						mpLinkString += ' <a href=' + 
							mpObject[mpObjectKeys[m]]['twitter'] + 
							' target=_blank rel="noopener noreferrer">Twitter page</a>,';
					}
					mpLinkString += ' at <a href=' + 
						mpObject[mpObjectKeys[m]]['hansardurl'] + 
						' target=_blank rel="noopener noreferrer">Hansard</a> and <a href=' + 
						mpObject[mpObjectKeys[m]]['twfuurl'] + 
						' target=_blank rel="noopener noreferrer">They Work For You</a>';
					linkList.push(mpObjectKeys[m] + ' ' + mpLinkString);

					linkList.push.apply(linkList, debateList[mpObjectKeys[m]]);
					linkList.push.apply(linkList, divisionList[mpObjectKeys[m]]);

					// assemble header images
					switch (mpObjectKeys[m])
					{
						case 'Alok Sharma':
							//imageString += '26583,';
							imageString += '9350,';
							//linkList.push(mpList[g] + ' <a href=https://www.aloksharma.co.uk/ target=_blank>home page</a>');
			
						break;
						case 'Matt Rodda':
							//imageString += '26584,';
							imageString += '9349,';
							//linkList.push(mpList[g] + ' <a href=https://www.mattrodda.net/ target=_blank>home page</a>');

						break;
					} // switch

					// assemble intro string
					//this.log("debateList[mpList[g]]).=" + JSON.stringify(debateList[mpList[g]]));
					//this.log("divisionList[mpList[g]]).=" + JSON.stringify(divisionList[mpList[g]]));

					debateListString = sortUnique(debateList[mpObjectKeys[m]]).join(" and ");
					divisionListString = sortUnique(divisionList[mpObjectKeys[m]]).join(" and ");
					introStringList = [];

					if ( debateListString && debateListString.length > 0 )
					{
						introStringList.push(" took part in debates on " + debateListString );
					} 
					if ( divisionListString && divisionListString.length > 0 )
					{
						introStringList.push(" voted on " + divisionListString );
					}
					if ( writtenQAList[mpObjectKeys[m]]['r'] && writtenQAList[mpObjectKeys[m]]['r'] > 0 )
					{
						introStringList.push(' answered ' + writtenQAList[mpObjectKeys[m]]['r'] + ' written question' + (writtenQAList[mpObjectKeys[m]]['r']>1?'s':'') );
					}
					if ( writtenQAList[mpObjectKeys[m]]['q'] && writtenQAList[mpObjectKeys[m]]['q'] > 0 )
					{
						introStringList.push(' got answers to ' + writtenQAList[mpObjectKeys[m]]['q'] + ' of ' +mpObject[mpObjectKeys[m]]['possessive_pronoun']  + ' written question' + (writtenQAList[mpObjectKeys[m]]['q']>1?'s':'') );
					}
					if ( oralQAList[mpObjectKeys[m]]['r'] && oralQAList[mpObjectKeys[m]]['r'] > 0 )
					{
						introStringList.push(' answered ' + oralQAList[mpObjectKeys[m]]['r'] + ' oral question' + (oralQAList[mpObjectKeys[m]]['r']>1?'s':'') );
					}
					if ( oralQAList[mpObjectKeys[m]]['q'] && oralQAList[mpObjectKeys[m]]['q'] > 0 )
					{
						introStringList.push(' got answers to ' + oralQAList[mpObjectKeys[m]]['q'] + ' of ' +mpObject[mpObjectKeys[m]]['possessive_pronoun']  + ' oral question' + (oralQAList[mpObjectKeys[m]]['q']>1?'s':'') );
					}
					if ( edmList[mpObjectKeys[m]] )
					{
						if ( edmList[mpObjectKeys[m]]['sponsored'] && edmList[mpObjectKeys[m]]['sponsored'] > 0 )
						{
							introStringList.push(' sponsored ' + edmList[mpObjectKeys[m]]['sponsored'] + ' early day motion' + (edmList[mpObjectKeys[m]]['sponsored']>1?'s':'') );
						}
						if ( edmList[mpObjectKeys[m]]['supported']  && edmList[mpObjectKeys[m]]['supported'] > 0 )
						{
							introStringList.push(' supported ' + edmList[mpObjectKeys[m]]['supported'] + ' early day motion' + (edmList[mpObjectKeys[m]]['supported']>1?'s':'') );
						}
					}

					introString += '<a href=' 
						+ mpObject[mpObjectKeys[m]]['twfuurl'] + ' target=_blank rel="noopener noreferrer">' 
						+ mpObjectKeys[m] + '</a> (' 
						+ mpObject[mpObjectKeys[m]]['party'] 
						+ ' MP for ' + mpObject[mpObjectKeys[m]]['constituency'] 
						+ ( mpObject[mpObjectKeys[m]]['office'] ? ' and ' +  mpObject[mpObjectKeys[m]]['office'] : '' ) + ')' 
						+ introStringList.join('. ' + properCase(mpObject[mpObjectKeys[m]]['subject_pronoun']) + ' ')
						+ '.<br><br>';
	
				} // for
			} // if

			// top and tail strings
			// TODO dont hardcode constituencies
			titleString = 'What ' + (mpObjectKeys.length == 1 ? 'has Reading MP ' : 'have Reading MPs ' ) + 
				mpObjectKeys.join(' and ') + 
				' been up to at Westminster since ' + earliestDate.getDate() + ' ' + monthNames[earliestDate.getMonth()] + '?';
				// mpItems[0].minDate.split('-')[2] + ' ' + monthNames[mpItems[0].minDate.split('-')[1] - 1] + '?';

			imageString = '[gallery type=rectangular ids=' + imageString.replace(/,\s*$/, '') + ' orderby=rand]<br>';
			introString += '<!--more-->';
			

			// add standard links
			linkList.push('MP expenses at the <a href=http://www.theipsa.org.uk/mp-costs/interactive-map/ target=_blank rel="noopener noreferrer">Independent Parliamentary Standards Authority</a>');
			linkList.push('<a href=https://hansard.parliament.uk/ target=_blank rel="noopener noreferrer">Hansard Online</a>');
			linkList.push('<a href=https://www.parliament.uk/ target=_blank rel="noopener noreferrer">Parliament Online</a>');
			linkList.push('<a href=https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/parliamentary-commissioner-for-standards/registers-of-interests/register-of-members-financial-interests/ target=_blank rel="noopener noreferrer">Register of members interests</a>');

			// assemble event for passage to Wordpress post creation routine
			this.createEvent(
				{ 
					"title"    	: titleString,
					"body"     	: imageString + introString + debateString + divisionString + oralQAstring + writtenQAstring + edmString + 
								"<hr><h5>Links</h5><ol><li>" + sortUnique(linkList).join("</li><li>") + "</li></ol>",
					"category" 	: "news, politics, " + sortUnique(wardList).join(" ward, ") + " ward",
					"delay"    	: tomorrow.getDate() + "-" + monthNames[tomorrow.getMonth()] + "-" + tomorrow.getFullYear() + " 09:00:00",
					"status"   	: "draft"
					// "credential"	: "{" + sortUnique(credential).join(',') + "}" // eg {"Reading East":"2018-09-14","Reading West":"2018-09-14"}
				}
			)

		} //if (print)
	    
	} //for(var i = 0; i < incomingEvents.length; i++)
  
} //Agent.receive = function()
