# This script pushes the metric of routes in and out, from and to all attachments of a transit gateway. It also pushes metric for total routes in a transit gateway.

from __future__ import print_function
import json
import boto3
import os

# Initialized boto3 clients used in this function
tgwregion = os.environ['tgwregion']
dynamodb = boto3.client('dynamodb', region_name='us-west-2')
ec2 = boto3.client('ec2', region_name=tgwregion)
cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')
ddbtableout= os.environ['ddbtableout']
ddbtablein= os.environ['ddbtablein']
namespace = os.environ['NameSpace']

#print('Loading function')


def lambda_handler(event, context):
#    print(event)
    response = ec2.describe_transit_gateway_attachments()
#    print (response)
#    print (len(response['TransitGatewayAttachments']))
#Iterate through the response of describe-transit-gateway-attachments api call calculate in and out prefic count for each attachment
    for i in range (len(response['TransitGatewayAttachments'])):
#        print (response['TransitGatewayAttachments'][i]['ResourceType']+", "+response['TransitGatewayAttachments'][i]['TransitGatewayAttachmentId']+", "+response['TransitGatewayAttachments'][i]['Association']['TransitGatewayRouteTableId'])
        TransitGatewayAttachmentId = response['TransitGatewayAttachments'][i]['TransitGatewayAttachmentId']
        TransitGatewayRouteTableId = response['TransitGatewayAttachments'][i]['Association']['TransitGatewayRouteTableId']
        ResourceType = response['TransitGatewayAttachments'][i]['ResourceType']
        ResourceId = response['TransitGatewayAttachments'][i]['ResourceId']
        DimensionName = ResourceType+"-"+ResourceId
        DimensionNameIn = DimensionName+"-IN"
        DimensionNameOut = DimensionName+"-Out"
        TransitGatewayId = response['TransitGatewayAttachments'][i]['TransitGatewayId']
        TGWTotal = TransitGatewayId+"-Total"
# Scan the DDB table to count routes advertised by the attachment to the TGW
        In = dynamodb.scan(
            TableName=ddbtablein,
            FilterExpression='#75c00 = :75c00',
            ExpressionAttributeNames={'#75c00':'tgwAttachmentId'},
            ExpressionAttributeValues={':75c00': {'S':TransitGatewayAttachmentId}}
        )
#        print (In['Count'])
# Push the incoming route counts to CloudWatch custom metric
        putMetricIn = cloudwatch.put_metric_data(
            MetricData=[
                {
                    'MetricName': 'Routes',
                    'Dimensions': [
                        {
                            'Name': DimensionName,
                            'Value': DimensionNameIn
                        },
                    ],
                    'Unit': 'Count',
                    'Value': (In['Count'])
                },
            ],
            Namespace=namespace
        )
#        print (putMetricIn)
# Scan the DDB table to count routes propagated to the attachment by TGW
        Out = dynamodb.scan(
            TableName=ddbtableout,
            FilterExpression = "#14260 = :14260 And #14261 <> :14261 And #14262 = :14262",
            ExpressionAttributeNames = {"#14260":"transitGatewayRouteTableId","#14261":"tgwAttachmentId","#14262":"routeState"},
            ExpressionAttributeValues = {":14260": {"S":TransitGatewayRouteTableId},":14261": {"S":TransitGatewayAttachmentId},":14262": {"S":"active"}}
        )
#        print (Out['Count'])
# Push the outgoing route counts to CloudWatch custom metric
        putMetricOut = cloudwatch.put_metric_data(
            MetricData = [
                {
                    'MetricName': 'Routes',
                    'Dimensions': [
                        {
                            'Name': DimensionName,
                            'Value': DimensionNameOut
                    },
                 ],
                    'Unit': 'Count',
                    'Value': (Out['Count'])
            },
            ],
            Namespace = namespace
            )
#        print(putMetricOut)
# Scan the DDB table to count total routes in TGW
        Total = dynamodb.scan(
            TableName=ddbtableout,
            FilterExpression = "#fb3f0 = :fb3f0",
            ExpressionAttributeNames = {"#fb3f0":"transitGatewayId"},
            ExpressionAttributeValues = {":fb3f0": {"S":TransitGatewayId}}
        )
# Push the total route counts to CloudWatch custom metric    
        putMetricTotal = cloudwatch.put_metric_data(
            MetricData=[
            {
                'MetricName': 'Routes',
                'Dimensions': [
                    {
                        'Name': TGWTotal,
                        'Value': 'Total'
                    },
                ],
                    'Unit': 'Count',
                    'Value': (Total['Count'])
                },
                ],
                Namespace = namespace
            )
#        print(putMetricTotal)
#        print (Total['Count'])
    