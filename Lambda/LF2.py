import json
import boto3
import datetime
from botocore.vendored import requests
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import decimal


def lambda_handler(event, context):
    
    
  

    
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
    SENDER = "Sender email id"
    RECIPIENT =recipient
    
    AWS_REGION = "Region Name"
    
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
    dynamodb = boto3.resource("dynamodb", region_name='Region Name')
    
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
    url="Elastic endpoint"+cuisine
    print("==================")
    response=requests.get(url)
    hotels=json.loads(response.text)['hits']['hits']
    suggestions=[]
    for place in hotels:
        suggestions.append(place['_id'])
    return suggestions
    
    
    
    
def SQSfetch():   
    client = boto3.client('sqs')
    response = client.receive_message(
        QueueUrl='Queue Address',
        AttributeNames=['All'],
        MessageAttributeNames=['cuisine','location','time','date','people']
    )
    return response
    
    
    
    
def SQSdelete(msgHandle):
    client = boto3.client('sqs')
    response = client.delete_message(
        QueueUrl='Queue Address',
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
    headers={'Authorization': 'Bearear Auth'}

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

    dynamodb = boto3.resource('dynamodb', region_name='Region Name')

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
   
    endpoint = 'Elastic Endpoint'
    
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
       
       API_ENDPOINT = "Dynamo endpoint"+item["id"]
       
       r = requests.post(url = API_ENDPOINT, data = data, headers=headers)
  data = json.dumps(data)
"""
