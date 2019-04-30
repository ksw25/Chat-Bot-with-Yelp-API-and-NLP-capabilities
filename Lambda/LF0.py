import json
#import requests
import boto3

def handler(event, context):
    # ans=[]
    # for key,val in event.items():
    #     ans.append(key)
    #     ans.append(val)
    uid="Test_619"   
    client = boto3.client('lex-runtime')
    response = client.post_text(
    botName='RestaurantChatBotLex',
    botAlias='RestaurantChatBotLex',
    userId=uid,
    inputText=event['message']
    )
    return {'statusCode': 200,'body': json.dumps(response['message'])}