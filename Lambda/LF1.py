
import math
import dateutil.parser
import datetime
import time
import os
import logging
from botocore.vendored import requests
import argparse
import json
import sys
import urllib
import boto3


# This client code can run on Python 2.x or 3.x.  Your imports can be
# simpler if you only need one of those.
try:
    # For Python 3.0 and later
    from urllib.error import HTTPError
    from urllib.parse import quote
    from urllib.parse import urlencode
except ImportError:
    # Fall back to Python 2's urllib2 and urllib
    from urllib2 import HTTPError
    from urllib import quote
    from urllib import urlencode
    

#Yelp API credentials
API_KEY="Your Yelp Key"
# API constants, you shouldn't have to change these.
API_HOST = 'https://api.yelp.com'
SEARCH_PATH = '/v3/businesses/search'
BUSINESS_PATH = '/v3/businesses/'  # Business ID will come after slash.

def request(host, path, api_key, url_params=None):
    """Given your API_KEY, send a GET request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        API_KEY (str): Your API Key.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    url = '{0}{1}'.format(host, quote(path.encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % api_key,
    }

    response = requests.request('GET', url, headers=headers, params=url_params)

    return response.json()


def search(api_key, term, location):
    """Query the Search API by a search term and location.
    Args:
        term (str): The search term passed to the API.
        location (str): The search location passed to the API.
    Returns:
        dict: The JSON response from the request.
    """

    url_params = {
        'term': term.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        'limit': 20
    }
    return request(API_HOST, SEARCH_PATH, api_key, url_params=url_params)


def get_business(api_key, business_id):
    """Query the Business API by a business ID.
    Args:
        business_id (str): The ID of the business to query.
    Returns:
        dict: The JSON response from the request.
    """
    business_path = BUSINESS_PATH + business_id

    return request(API_HOST, business_path, api_key)


def query_api(term, location):
    """Queries the API by the input values from the user.
    Args:
        term (str): The search term to query.
        location (str): The location of the business to query.
    """
    response = search(API_KEY, term, location)

    businesses = response.get('businesses')

    if not businesses:
        print(u'No businesses for {0} in {1} found.'.format(term, location))
        return

    business_id = businesses[0]['id']

    print(u'{0} businesses found, querying business info ' \
        'for the top result "{1}" ...'.format(
            len(businesses), business_id))
    l=len(businesses)
    output=''
    for i in range(l):
        response = get_business(API_KEY, businesses[i]['id'])
        output=output+'hi'
        #output+=str(i+1)+') '+response['name']+'\n\t'+','.join(response['location']['display_address'])+'\n\t'+response['phone']+'\n\n'
    return output


# Defaults for our simple example.
DEFAULT_TERM = ''
DEFAULT_LOCATION = 'New york'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def validate_request(cuisine, location, time, date, people):
    if people is not None:
        people = int(people)
        if people > 50 or people < 1:
            return build_validation_result(False,
                                      'PersonCount',
                                      'Please specify number of people betweek 1 to 50')
    
    places=['new york', 'manhattan', 'brooklyn', 'california', 'arizona', 'boston', 'new jersey', 'texas']
    if location is not None and location.lower() not in places:
        return build_validation_result(False,
                                       'Location',
                                       'Sorry, we do not have any recommendations for restaurants in {} yet.'.format(location))
                                       
    menu = ['mexican', 'indian', 'italian', 'south indian']
    if cuisine is not None and cuisine.lower() not in menu:
        return build_validation_result(False,
                                       'CuisineType',
                                       'Sorry, we do not have any recommendations for {} restaurants.'.format(cuisine))

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'Date', 'I did not understand that, what date would you like to go?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'Date', 'Please enter a present or future date.')

    if time is not None:
        if len(time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', 'Invalid Time. Please enter the time of visit again.')

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', 'Invalid time. Please enter again.')

        if hour < 9 and hour > 2:
            # Outside of business hours
            return build_validation_result(False, 'Time', 'Our business hours are from morning 9 a m. to night 2 a m. Can you specify a time during this range?')

    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """

def greet(intent_request):
    return {
        'dialogAction': {
            "type": "ElicitIntent",
            "message": {
                "contentType": "PlainText", 
                "content": "Hi, how can I help you?"}
        }
    }
    

def yelpAPI(cuisine, location, time, date, people):
    parser = argparse.ArgumentParser()
    cuisine=cuisine+'food'
    parser.add_argument('-q', '--term', dest='term', default=cuisine,
                        type=str, help='Search term (default: %(default)s)')
    parser.add_argument('-l', '--location', dest='location',
                        default=location, type=str,
                        help='Search location (default: %(default)s)')
    #parser.add_argument('-c', '--categories', dest='categories', default='Indian food', type=str)
    #parser.add_argument('-o', '--open_at', dest='open_at', default=1552917480, type=int)
    
    
    input_values = parser.parse_args()

    try:
        query_api(input_values.term, input_values.location)
    except HTTPError as error:
        sys.exit(
            'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                error.code,
                error.url,
                error.read(),
            )
        )
    
def restaurantApiCall(requestData):
    
    url = "https://api.yelp.com/v3/businesses/search"
    
    querystring = requestData
    
    payload = ""
    headers={'Authorization': 'Bearer NYNyWecq6QWYX2CYmYmyQKJGAdEFMSzvTC2tYaSJ8gAXwbjjwyhlmllPXKM28CH1sm8ApCXo3KonuBLisKVX-cS0V__LDBX8cm6rJkMaP1Q5Pz9DE4tB-1n8c3CNXHYx'}
    
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    message = json.loads(response.text)
    
    if len(message['businesses']) < 1:
        return 'There is no restaurants under this description'
    
    textString = "Hey! Here are our restaurant suggestions:"
    count = 1
    for business in message['businesses']:
        textString = textString + " " + str(count) + ") " + business['name'] + ", " + business['location']['address1'] + ", " + business['phone']
        count += 1
    
    textString = textString + ". Have a great day!"
    print("In restaurantApiCall, ",textString)
    return textString
    
    
def findRestaurants(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    cuisine = get_slots(intent_request)["CuisineType"]
    location = get_slots(intent_request)["Location"]
    time = get_slots(intent_request)["Time"]
    date = get_slots(intent_request)["Date"]
    people = get_slots(intent_request)["PersonCount"]
    email=get_slots(intent_request)["email"]
    source = intent_request['invocationSource']
    
    

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)
        
        validation_result = validate_request(cuisine, location, time, date, people)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request))
    
    att = {
        'cuisine':{
            'StringValue':str(cuisine),
            'DataType':'String'
            },
        "location":{
            'StringValue':str(location),
            'DataType':'String'
            },
        "time":{
            'StringValue':str(time),
            'DataType':'String'
            },
        "date":{
            'StringValue':str(date),
            'DataType':'String'
            },
        "people":{
            'StringValue':str(people),
            'DataType':'String'
            },
        "email":{
            'StringValue':str(email),
            'DataType':'String'
            }
            
    }     
    
    client = boto3.client('sqs')
    response = client.send_message(
        QueueUrl='Your Queue Url',
        MessageBody=json.dumps(att),
        MessageAttributes=att
    )
    
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': "Thanks you for giving us an opportunity to serve you. Please check your inbox for an email with the recommendations arriving shortly."})


def thankYou(intent_request):
    return {
        'dialogAction': {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                "contentType": "PlainText", 
                "content": "Thank you for giving us an opportunity to serve you. Have a great day!"}
        }
    }

""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GreetingIntent':
        return greet(intent_request)
    elif intent_name == 'OrderFood':
        return findRestaurants(intent_request)
    else:
        return thankYou(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)
