## How to Monitor AWS Transit Gateway Route Limits using Serverless Architecture

AWS Transit Gateway (TGW) simplifies management and reduces operational costs of networks within your AWS environments and connectivity from on-premises networks. AWS Transit Gateway provides you with the ability to connect multiple Amazon Virtual Private Clouds (VPC) , Virtual Private Networks (VPN) and scale up to 5,000 attachments and 10000 Routes spread across multiple route tables. Each of these attachments have certain limits on number of prefixes which can be advertised to and from AWS Transit Gateway. Monitoring these limits from AWS console or CLI becomes a challenge as and when the number of attachments increase over time. If these limits are not monitored and proactive actions such as route summarization are not taken to keep the number of prefixes under limits, it can cause unexpected disruptions to your network. 

For knowing the limits of different attachments please click on the below links:
•	VPN Attachments
•	Connect Attachments
•	Direct Connect (Transit Virtual Interface) Attachments

In this blog we walkthrough a serverless solution to monitor and get alerts on route limits of AWS Transit Gateway attachments. Below is the schematic of the solution which utilizes AWS Cloudwatch, AWS Transit Gateway Network Manager, Amazon Lambda and Amazon DynamoDB.

## Solution Architecture:

![alt text](https://github.com/aws-samples/how-to-monitor-tgw-route-limits-using-serverless-architecture/blob/main/TGWRouteMonitoring.jpg)

## Solution Overview:

The solution initializes with running an Amazon Lambda function to capture the current state of AWS Transit Gateways in your account in a given region. This information is written to an Amazon DynamoDB table. Next the solution listens for any Routing Updates events sent by AWS Transit Gateway Network Manager to AWS CloudWatch Logs which in turn triggers an Amazon Lambda to update the above mentioned Amazon DynamoDB. Based on the event the Amazon Lambda function adds or removes the routes installed or uninstalled from the AWS Transit Gateways in your account in a given region.

The solution also deploys an Amazon Lambda function which runs every minutes to scan the Amazon DynamoDB table mentioned above and calculates the number of prefixes advertised to and from each attachments of each AWS Transit Gateway in your account in a given region. Once this information is processed, the AWS Lambda function pushes the metrics to AWS CloudWatch using customer metric push API.

You can use these metrics to create dashboards and alerts base on the limits of each attachments, by following the instructions in AWS CloudWatch Documentation. 
Prerequisites
Readers of this blog post should be familiar with the following AWS services:
•	AWS Transit Gateway
•	AWS Transit Gateway Network Manager
•	AWS CloudFormation
•	AWS Lambda
•	AWS CloudWatch
•	Amazon DynamoDB
•	Amazon S3

For this walkthrough, you should have the following:
•	AWS Account
•	AWS Command Line Interface (AWS CLI): You need AWS CLI installed and configured on the workstation from where you are going to try the steps mentioned below.
•	Credentials configured in AWS CLI should have the required IAM permissions to spin up and modify the resources mentioned in this post.
•	Make sure that you deploy the solution to us-west-2 Region and your AWS CLI default Region is us-west-2. If us-west-2 is not the default Region, reference the Region explicitly while executing AWS CLI commands using --region us-west-2 switch.
•	Amazon S3 bucket in us-west-2 region for staging Lambda deploy packages
•	Amazon S3 buckets in the regions where you want to monitor the routes limits of AWS Transit Gateways.
•	One or more AWS Transit Gateways with attachments and route tables configured.
•	AWS Transit Gateway Network Manager should be configured to monitor all AWS Transit Gateways in your account.

## Walk Through:
1.	Create an Amazon S3 bucket in us-west-2 for staging the deployment packages.    <code> aws s3api create-bucket --bucket <bucket-name> --region us-west-2 </code>
2.	Create an Amazon S3 bucket in the region where the AWS Transit Gateway you are planning to monitor is present. For example below snippet created the bucket in us-east-1.                                    aws s3api create-bucket --bucket <bucket-name> --region us-east-1
3.	Download and unzip the file containing AWS CloudFormation template and Amazon Lambda function code from here to a folder in your local workstation. You will need to run all of the subsequent commands from this folder.
4.	Zip the Amazon Lambda functions init_lambda_function.py, update_lambda_function.py and put_metric_lambda_function.py and upload it to an Amazon S3 bucket you created in step 1.
$ zip init_lambda_function.py init_lambda_function.py.zip
$ zip update_lambda_function.py update_lambda_function.py.zip
$ zip put_metric_lambda_function.py put_metric_lambda_function.py.zip
$ aws s3 cp init_lambda_function.py.zip s3://<bucket-name-from-step-1>/
$ aws s3 cp update_lambda_function.py.zip s3://<bucket-name-from-step-1>/
$ aws s3 cp put_metric_lambda_function.py.zip s3://<bucket-name-from-step-1>/
5.	Create the resources required for this blog post by deploying the AWS CloudFormation template and running the below command:
aws cloudformation create-stack \
--stack-name TgwRouteMonitoring \
--template-body file://TGWRouteMonitoring.yml \
--parameters ParameterKey=CloudWatchMetricNameSpace,ParameterValue=TGWRoutes
 ParameterKey=S3BucketWithDeploymentPackage,ParameterValue=<bucket-name-from-step-1> ParameterKey=S3BucketForTGWRoutesExport,ParameterValue=<bucket-name-from-step-2> ParameterKey=TGWRegion,ParameterValue=<region-of-tgw-you-want-to-monitor \
--capabilities CAPABILITY_IAM \
--region us-west-2
You need to provide the following information, and you can change the parameters based on your specific needs:
a.     CloudWatchMetricNameSpace is the AWS CloudWatch metric name space under which all the route metrics will be pushes. 
b.     S3BucketWithDeploymentPackage. Name of Amazon S3 bucket used in step 1. This will have the deployment package for all the Amazon Lambda functions used in this blog.
c.     S3BucketForTGWRoutesExport. Name of Amazon S3 bucket used in step 2. This will be used to store the route table exported to capture the initial state of AWS Transit Gateways, its attachments and the number of routes in the route tables. 
d.     TGWRegion. Region where the AWS Transit Gateways you want to monitor are present.
Some stack templates might include resources that can affect permissions in your AWS account, for example, by creating new AWS Identity and Access Management (IAM) role. For those stacks, you must explicitly acknowledge this by specifying CAPABILITY_IAM or CAPABILITY_NAMED_IAM value for the –capabilities parameter.
Stack creation will take you approximately 5-7 minutes. Check the status of the stack by executing the below command every few minutes. You should see StackStatus value as CREATE_COMPLETE.
Example:
aws cloudformation describe-stacks --stack-name TgwRouteMonitoring | grep StackStatus
The CloudFormation template will create the following resources:
•	One Amazon DynamoDB table (Logical ID: RoutesDDBTable) with 5 Read and Write Capacity Units (RCU and WCU), used to store all the required parameters to monitor the number of routes. It also creates Write Scaling Policy for Amazon DynamoDB to scale the WCUs to max of 15.
•	InitLambdaFunction (init_lambda_function.py) with required IAM permissions to export AWS Transit Gateway routes and populate the Amazon DynamoDB Table.
•	UpdateLambdaFunction (update_lambda_function.py) with required IAM permissions to track AWS Transit Gateway route install and uninstall events and update the Amazon DynamoDB table accordingly. 
•	PutMetricLambdaFunction (put_metric_lambda_function.py) with required IAM permissions to scan the Amazon DynamoDB table, calculate per attachment incoming and outgoing routes advertisements and then push the metrics to AWS CloudWatch. 
•	AWS CloudWatch event rule to trigger UpdateLambdaFunction as and when there is a AWS Transit Gateway route install and uninstall event. 
•	AWS CloudWatch schedule rule with required IAM permissions to invoke PutMetricLambdaFunction every minute which will scan the Amazon DynamoDB, calculate per attachment incoming and outgoing routes advertisements and then push the metrics to AWS CloudWatch.
•	AWS CloudWatch schedule rule with required IAM permissions to invoke InitLambdaFunction every 60 minute. This function will export the routes in AWS Transit Gateway route tables to and Amazon S3 bucket and then parse the data and update the Amazon DynamDB table. 
Once the stack is deployed, we need to populate the Amazon DynamoDB table with current state of AWS Transit Gateways and route tables. We do that by invoking the InitLambdaFunction manually from AWS CLI. For that we need the physical id of the function. We do that by describing the AWS CloudFormation template as shown below:
$ aws cloudformation describe-stack-resources --stack-name TGWRTMON --region us-west-2 | grep InitLambdaFunction

"PhysicalResourceId": "TGWRTMON-InitLambdaFunction-1E4ONARQ02SM3", 
"LogicalResourceId": "InitLambdaFunction"

Use the value of PhysicalResourceId from the above output to invoke the function, as shown in the below command:
$ aws lambda invoke --function-name TGWRTMON-InitLambdaFunction-1E4ONARQ02SM3 response.json --region us-west-2


On successful invocation of the function, you should see the below output. 

{
    "ExecutedVersion": "$LATEST", 
    "StatusCode": 200
}

At this point all the required components are in place to monitor the number of routes per attachment per AWS Transit Gateway. InitLambdaFunction has populated the Amazon DynamoDB table, UpdateLambdaFunction will be triggered as and when there is a AWS Transit Gateway route install or uninstall event and PutMetricLambda is calculating the routes per attachment every minute and pushing it to AWS CloudWatch.

To view the metrics in AWS Management Console, navigate to CloudWatch, then to  Metrics and then click on the Custom Namespace created by the PutMetricLambdaFunction. Under the namespace will be the Metrics for each attachment depicted by its attachment-id and its corresponding dimensions (IN our OUT). Useful statistic for these metrics is ‘Sample Count’ for period of 1 minute. You can use these metrics to create dashboards and alerts base on the limits of each attachments, by following the instructions in AWS CloudWatch Documentation. 

Clean Up
•	Empty and delete the S3 bucket created in Step 1 and 2. 
•	Delete CloudFormation stack created in Step 5.

Conclusion
In this blog post, we demonstrated how to monitor the number of routes per attachment per AWS Transit Gateway using AWS CloudWatch and serverless solution. You can use these metrics to create alarms in AWS CloudWatch to get notification as and when the number of routes are approaching its corresponding attachment limit and take proactive action to keep the routes within limits.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

