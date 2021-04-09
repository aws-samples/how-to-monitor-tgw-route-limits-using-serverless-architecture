# This function populates the DDB with existing TGW routes. This should be executed before deploying the route
# monitoring solution. It can also ran anythime thre is discrapancy betweent he DDB table and actual routes in TGW.

from __future__ import print_function
import boto3
import json
import os


# Initializing boto3 clients used in this function
tgwregion = os.environ['tgwregion']
ec2 = boto3.client('ec2', region_name=tgwregion)
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb', region_name='us-west-2')
s3bucket= os.environ['s3bucket']
ddbtable= os.environ['ddbtable']

def lambda_handler(event, context):
    
    # Specifying the S3 bucket to be used for storing the route export json outputs. Please replace this with your S3 bucket.
    # Getting all the TGW route tables in the account
    response = ec2.describe_transit_gateway_route_tables()
    print (response)
    # Exporting all the routes to the S3 bucket specified earlier in the code. The json output files will be
    # stored in /VPCTransitGateway/TransitGatewayRouteTables/ folder
    for i in range (len (response['TransitGatewayRouteTables'])):
        response1 = ec2.export_transit_gateway_routes(
            TransitGatewayRouteTableId= response['TransitGatewayRouteTables'][i]['TransitGatewayRouteTableId'],
            S3Bucket=s3bucket
            )
    #    print (response1)
    # Extracting json file name with path from output of route export API call
        Object_Name_Split = response1['S3Location'].split("//")
    #    print (Object_Name_Split)
        ObjectsPath = Object_Name_Split[1].split("/")
        Object = ObjectsPath[1]+"/"+ObjectsPath[2]+"/"+ObjectsPath[3]
    #    print (Object)
    # Downloading json file to /tmp to be processed by Lambda function
        s3.download_file(s3bucket, Object, '/tmp/rt-json.json')
    # Extracting the columns for DDB table from the json file
        with open('/tmp/rt-json.json') as f:
            records = json.load(f)
            routeRecords = records['routes']
            for record in routeRecords:
    # Blackholed routes need to be proccessed differently when compared with other routes.
                if record['state'] == 'blackhole':
                    destinationCidrBlock = record['destinationCidrBlock']
                    attachmentType = ""
                    resourceId = ""
                    routeState = record['state']
                    routeType = record['type']
#                    protocol = ""
                    tgwAttachmentId = ""
                    transitGatewayRouteTableId = response['TransitGatewayRouteTables'][i]['TransitGatewayRouteTableId']
                    blackholeTgw = ec2.describe_transit_gateway_route_tables(
                        TransitGatewayRouteTableIds=[
                            transitGatewayRouteTableId,
                        ]
                    )
                    transitGatewayId = blackholeTgw['TransitGatewayRouteTables'][0]['TransitGatewayId']
                    blackholeAccount = ec2.describe_transit_gateways(
                        TransitGatewayIds=[
                            transitGatewayId,
                        ]
                    )
                    account = blackholeAccount['TransitGateways'][0]['OwnerId']
                    print(destinationCidrBlock)
                    print(attachmentType)
                    print(resourceId)
                    print(routeState)
                    print(routeType)
                    print(transitGatewayRouteTableId)
                    print(transitGatewayId)
                    print(account)
    # Adding items to DDB table for blackholed routes
                    ddbputblackhole = dynamodb.put_item(
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
                    print (ddbputblackhole)
    # Extracting columns for DDB table for routes other than status of blackhole
                else:
                    destinationCidrBlock = record['destinationCidrBlock']
                    print (destinationCidrBlock)
                    attachmentType = record['transitGatewayAttachments'][0]['resourceType']
                    print(attachmentType)
                    resourceId = record['transitGatewayAttachments'][0]['resourceId']
                    print (resourceId)
                    routeState = record['state']
                    print (routeState)
                    routeType = record['type']
                    print (routeType)
                    tgwAttachmentId = record['transitGatewayAttachments'][0]['transitGatewayAttachmentId']
                    print (tgwAttachmentId)
                    remaining = ec2.describe_transit_gateway_attachments(
                        TransitGatewayAttachmentIds = [tgwAttachmentId]
                    )
                    transitGatewayRouteTableId=response['TransitGatewayRouteTables'][i]['TransitGatewayRouteTableId']
                    print (transitGatewayRouteTableId)
                    account = remaining['TransitGatewayAttachments'][0]['TransitGatewayOwnerId']
                    print (account)
                    transitGatewayId = remaining['TransitGatewayAttachments'][0]['TransitGatewayId']
                    print (transitGatewayId)
                    protocol = ""
    # Adding items to DDB table for routed other than blackholed routes
                    ddbputnonblackhole = dynamodb.put_item(
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
                    print (ddbputnonblackhole)

    