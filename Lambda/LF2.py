import json
import boto3
import datetime
from botocore.vendored import requests
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import decimal


def lambda_handler(event, context):
    
    
    #restos=[]
    #restos=[{'id': 'xq0cX_DgxiJMXwhmEl9kUA', 'alias': 'café-china-new-york-2', 'name': 'Café China', 'image_url': 'https://s3-media2.fl.yelpcdn.com/bphoto/XSudwvbbAfYFYZViZB5ucw/o.jpg', 'is_closed': False, 'url': 'https://www.yelp.com/biz/caf%C3%A9-china-new-york-2?adjust_creative=uE4YsWaGl3VEU91vRGXLow&utm_campaign=yelp_api_v3&utm_medium=api_v3_business_search&utm_source=uE4YsWaGl3VEU91vRGXLow', 'review_count': 1382, 'categories': [{'alias': 'szechuan', 'title': 'Szechuan'}], 'rating': 4.0, 'coordinates': {'latitude': 40.7499225208569, 'longitude': -73.9819464127197}, 'transactions': ['pickup', 'restaurant_reservation', 'delivery'], 'price': '$$', 'location': {'address1': '13 E 37th St', 'address2': None, 'address3': '', 'city': 'New York', 'zip_code': '10016', 'country': 'US', 'state': 'NY', 'display_address': ['13 E 37th St', 'New York, NY 10016']}, 'phone': '+12122132810', 'display_phone': '(212) 213-2810', 'distance': 1180.6956479004084},{'id': 'ojbH3wnRu050hRhkmoxRiA', 'alias': 'han-dynasty-new-york-4', 'name': 'Han Dynasty', 'image_url': 'https://s3-media3.fl.yelpcdn.com/bphoto/fe5QaNZH6Qc-dbIDPwE2Ww/o.jpg', 'is_closed': False, 'url': 'https://www.yelp.com/biz/han-dynasty-new-york-4?adjust_creative=uE4YsWaGl3VEU91vRGXLow&utm_campaign=yelp_api_v3&utm_medium=api_v3_business_search&utm_source=uE4YsWaGl3VEU91vRGXLow', 'review_count': 514, 'categories': [{'alias': 'szechuan', 'title': 'Szechuan'}], 'rating': 4.0, 'coordinates': {'latitude': 40.78752, 'longitude': -73.97647}, 'transactions': ['pickup', 'restaurant_reservation', 'delivery'], 'price': '$$', 'location': {'address1': '215 W 85th St', 'address2': '', 'address3': '', 'city': 'New York', 'zip_code': '10024', 'country': 'US', 'state': 'NY', 'display_address': ['215 W 85th St', 'New York, NY 10024']}, 'phone': '+12128589060', 'display_phone': '(212) 858-9060', 'distance': 3045.824094143192}]
    #insertDynamo(restos)
    #insertElasticSearch(restos)


  #  loadDynamoAndElastic()
    
    message=SQSfetch()
    #print(message)
   
    if 'Messages' in message:
        msgHandle=message['Messages'][0]['ReceiptHandle']
        msgCuisine=json.loads(message['Messages'][0]['Body'])['cuisine']['StringValue']
        print(msgCuisine)
        print(json.loads(message['Messages'][0]['Body'])['email']['StringValue'])
        recipient=json.loads(message['Messages'][0]['Body'])['email']['StringValue']
        businessIdList=elasticSearch(msgCuisine)
        print(businessIdList)
        
        places=[]
        for i in range(1,6):
            result=dynamoSearch(businessIdList[i-1])
            places.append(str(i)+') '+result['hotelName']+', '+result['hotelAddress']+"<br>")
        
        SQSdelete(msgHandle)
        print(places)
        #verifyEmail(recipient)
        
        result = ''.join(places)
        sendEmail(result,recipient)
    
    
def verifyEmail(emailId):
    client = boto3.client('ses')
    response = client.verify_email_identity(
    EmailAddress=emailId)


def sendEmail(resultData,recipient):
    SENDER = "ksw352@nyu.edu"
    RECIPIENT =recipient
    #RECIPIENT = "karan25aug@gmail.com"
    AWS_REGION = "us-east-1"
    
    SUBJECT = "Restaurant Recommendations"
    
    BODY_TEXT = ("Amazon project (Python)")
            
    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
      <p>Hey there, we recommend the following restaurants for your dining preferences</p>
      <p>""" + resultData + """</p>
      <p>Hope you have a great time. Thank you for giving us this opportunity to assist you.</p>
    </body>
    </html>
                """         
    
    # The character encoding for the email.
    CHARSET = "UTF-8"
    
    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)
    
    # return true
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Source=SENDER,
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Data': SUBJECT,
                },
            },
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def dynamoSearch(ID):
    dynamodb = boto3.resource("dynamodb", region_name='us-east-1')
    
    table = dynamodb.Table('yelp-rest')
    
    try:
        response = table.get_item(
            Key={
                'ID': ID
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        item = response['Item']
        hotelAddress=''
        hotelName = item['info']['name']
        for location in item['info']['display_address']:
            hotelAddress+=location+' '
        return {'hotelName':hotelName, 'hotelAddress':hotelAddress}
    
    
    
    
def elasticSearch(cuisine):
    
    """if(cuisine=="indian"):
        cuisine="Indian"
    elif(cuisine=="mexican"):
        cuisine="Mexican"
    elif(cuisine=="italian"):
        cuisine="Italian"
    elif(cuisine=="chinese"):
        cuisine="Chinese"
    elif(cuisine=="lebanese"):
        cuisine="Lebanese"
    """
    url="https://search-resto-search-66oaw6qdzs3evbybend3wma2ym.us-east-1.es.amazonaws.com/restaurants/_search?q=cuisine:"+cuisine
    print("==================")
    #url = 'https://search-resto-search-hon6f7himq5oe47d42a2bdnh4y.us-east-1.es.amazonaws.com/restaurants/_search?q=cuisine:Indian'
    response=requests.get(url)
    hotels=json.loads(response.text)['hits']['hits']
    suggestions=[]
    for place in hotels:
        suggestions.append(place['_id'])
    return suggestions
    
    
    
    
def SQSfetch():   
    client = boto3.client('sqs')
    response = client.receive_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/152218969335/cdtsqs',
        AttributeNames=['All'],
        MessageAttributeNames=['cuisine','location','time','date','people']
    )
    return response
    
    
    
    
def SQSdelete(msgHandle):
    client = boto3.client('sqs')
    response = client.delete_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/152218969335/cdtsqs',
        ReceiptHandle=str(msgHandle)
    )
    



def loadDynamoAndElastic():
    restos=[]
    for cuisine in ['Indian', 'Mexican', 'Italian', 'Chinese', 'Lebanese']:
        
        restos=yelp(cuisine)
        
        insertDynamo(restos)
        
        insertElasticSearch(restos)
   
   
   
        
def yelp(cuisine):
    url = "https://api.yelp.com/v3/businesses/search"
    payload = ""
    headers={'Authorization': 'Bearer NYNyWecq6QWYX2CYmYmyQKJGAdEFMSzvTC2tYaSJ8gAXwbjjwyhlmllPXKM28CH1sm8ApCXo3KonuBLisKVX-cS0V__LDBX8cm6rJkMaP1Q5Pz9DE4tB-1n8c3CNXHYx'}

    recommendation=[]
    for i in range(10):
        requestData = {
                        "term":cuisine+", restaurants",
                        "location":'Manhattan',
                        "categories":"Food",
                        "limit":"50",
                        "offset": 50*i
                    }
    
        response = requests.request("GET", url, data=payload, headers=headers, params=requestData)
        message = json.loads(response.text)
    
        if len(message['businesses']) < 1:
            return []
    
        recommendation+= message['businesses']
    
    return recommendation




def insertDynamo(restos):

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    table = dynamodb.Table('yelp-rest')

   
    
    for place in restos:
        if not place['id']:
            continue
        details={
            'id': place['id'],
            'alias': place['alias'],
            'name': place['name'],
            'is_closed': place['is_closed'],
            'categories': place['categories'],
            'rating': int(place['rating']),
            'review_count': place['review_count'],
            'transactions': place['transactions'],
            'zip_code': place['location']['zip_code'],
            'display_address': place['location']['display_address']
        }
       # print(details)
        
        if (place['image_url']):
            details['image_url'] = place['image_url']
        
        if (place['coordinates'] and place['coordinates']['latitude'] and place['coordinates']['longitude']):
            details['latitude'] = str(place['coordinates']['latitude'])
            details['longitude'] = str(place['coordinates']['longitude'])
            
        if (place['phone']):
            details['phone'] = place['phone']
        print(details['id'])
        try:
            response=table.put_item(
                   Item={
                       'ID': (details['id']),
                       'info': details,
                       'insertedAtTimestamp': str(datetime.datetime.now())
                    }
                )
            
           # print("PutItem succeeded:")
            #print(json.dumps(response, indent=4))
        except:
            print("error")
            continue




def insertElasticSearch(restos):
   # https://search-resto-search-66oaw6qdzs3evbybend3wma2ym.us-east-1.es.amazonaws.com
    endpoint = 'https://search-resto-search-66oaw6qdzs3evbybend3wma2ym.us-east-1.es.amazonaws.com/restaurants/Restaurant'
    
    headers = {'Content-type': 'application/json'}
       
    for place in restos:
        if not place['id']:
            continue
        url=endpoint+"/"+place['id']
        print(place['categories'][0]['title'])
        requestData = {
                           "id":place['id'],
                            "cuisine":place['categories'][0]['title']
                        }
        data=json.dumps(requestData)
    
        try:
            response = requests.put(url=url, data=data, headers=headers)
        except:
            continue
        
"""
  headers = {'Content-type': 'application/json'}
       
       API_ENDPOINT = "https://search-restaurants-yegdabho2nnbw7j2k4hkugyo5m.us-east-1.es.amazonaws.com/restaurants/Restaurant/"+item["id"]
       
       r = requests.post(url = API_ENDPOINT, data = data, headers=headers)
  data = json.dumps(data)
"""