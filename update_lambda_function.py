# This function gets triggered by CloudWatch events matching 'TGW-ROUTE-UNINSTALLED' or 'TGW-ROUTE-INSTALLED' and then extracts the required parameters from the logs to delete or add records to the DynamoDb table.

from __future__ import print_function
import json
import boto3
import os

# Initialize boto3 clients used in this function
tgwregion = os.environ['tgwregion']
dynamodb = boto3.client('dynamodb', region_name='us-west-2')
ddbtable = os.environ['ddbtable']

#print('Loading function')

def lambda_handler(event, context):
#    print(event)
# Extracting Prefix and RouteTableId from the event when an route is un-installed from TGW route tables.
    if (event['detail']['changeType'] == 'TGW-ROUTE-UNINSTALLED'):
        i = 0
        j = 0
        for destinationCidrBlock in event['detail']['routes']:
            for routeTable in event['detail']['transitGatewayRouteTableArns']:
                print(destinationCidrBlock)
                print(routeTable)
                routeTable_split = routeTable.split("/")
                print(routeTable_split)
                print(event['detail']['routes'][i]['destinationCidrBlock'])
                deleteRoute = (event['detail']['routes'][i]['destinationCidrBlock'])
                print(routeTable_split[1])
                fromRouteTable = routeTable_split[1]
                j = j + 1
# Delete the prefix from the DDB table
                response = dynamodb.delete_item(
                    Key={
                        'destinationCidrBlock': {
                            'S': deleteRoute,
                        },
                        'transitGatewayRouteTableId': {
                            'S': fromRouteTable,
                        },
                    },
                    TableName=ddbtable,
                )
#                print(response)
            i = i + 1
# If its not route un-install event the extract all the relevsnt fields to add the route in DDB table
    else:
        for destination in event['detail']['routes']:
#            print(destination)
            i = 0
            for routeTable in event['detail']['transitGatewayRouteTableArns']:
                account = event['account']
#                print(account)
                transitGatewayArn = (event['detail']['transitGatewayArn']).split("/")
                transitGatewayId = transitGatewayArn[1]
#                print(transitGatewayId)
                routeTable_split = routeTable.split("/")
                transitGatewayRouteTableId = routeTable_split[1]
#                print(transitGatewayRouteTableId)
                destinationCidrBlock = event['detail']['routes'][i]['destinationCidrBlock']
#                print(destinationCidrBlock)
                routeType = event['detail']['routes'][i]['routeType']
#                print(routeType)
                routeState = event['detail']['routes'][i]['routeState']
#                print(routeState)
                if routeState == 'blackhole':
                    tgwAttachmentId = ""
                    resourceId = ""
                    attachmentType = ""
#                    protocol = 'static'
                else:
                    j = 0
#                    print(len(destination['attachments']))
                    for attachments in destination['attachments']:
                        if j > (len(destination['attachments']) - 1):
                            break
                        tgwAttachmentId = (destination['attachments'][j]['tgwAttachmentId'])
#                        print(tgwAttachmentId)
                        resourceId = (destination['attachments'][j]['resourceId'])
#                        print(resourceId)
                        attachmentType = (destination['attachments'][j]['attachmentType'])
#                        print(attachmentType)
                        if attachmentType == 'vpn' and routeType == 'route_static':
                            protocol = 'static'
                        elif attachmentType == 'vpn':
                            protocol = event['detail']['routes'][i]['propagatedRouteFamily']
#                            print(protocol)
                        elif attachmentType == 'connect' and routeType == 'route_static':
                            protocol = 'static'
                        elif attachmentType == 'connect':
                            protocol = event['detail']['routes'][i]['propagatedRouteFamily']
#                            print(protocol)
                        elif attachmentType == 'vpc' and routeType == 'route_static':
                            protocol = 'static'
                        elif attachmentType == 'vpc':
                            protocol = event['detail']['routes'][i]['propagatedRouteFamily']
#                            print(protocol)
                        elif attachmentType == 'direct_connect_gateway' and routeType == 'route_static':
                            protocol = 'static'
                        elif attachmentType == 'direct_connect_gateway':
                            protocol = event['detail']['routes'][i]['propagatedRouteFamily']
#                            print(protocol)
                        elif attachmentType == 'peer_tgw':
                            protocol = 'static'
#                            print(protocol)
# Add the record to DDB table
                response = dynamodb.put_item(
                    Item={
                        'account': {
                            'S': account,
                        },
                        'transitGatewayId': {
                            'S': transitGatewayId,
                        },
                        'transitGatewayRouteTableId': {
                            'S': transitGatewayRouteTableId,
                        },
                        'destinationCidrBlock': {
                            'S': destinationCidrBlock,
                        },
                        'routeType': {
                            'S': routeType,
                        },
                        'routeState': {
                            'S': routeState,
                        },
                        'tgwAttachmentId': {
                            'S': tgwAttachmentId,
                        },
                        'resourceId': {
                            'S': resourceId,
                        },
                        'attachmentType': {
                            'S': attachmentType,
                        },
                    },
                    ReturnConsumedCapacity='TOTAL',
                    TableName=ddbtable,
                )
#                print(response)
                j = j + 1
            i = i + 1
