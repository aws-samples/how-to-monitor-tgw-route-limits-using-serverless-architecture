# **How to Monitor AWS Transit Gateway Route Limits using Serverless Architecture**

  <a href="https://aws.amazon.com/transit-gateway/">AWS Transit Gateway</a> simplifies your network and puts an end to complex peering relationships. It acts as a cloud router and scales elastically based on the volume of network traffic. It can centralize connections (known as attachments) from your on-premises networks, and attach to <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html">Amazon Virtual Private Clouds (VPC)</a> <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpn-attachments.html">Virtual Private Networks (VPN)</a>, <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-dcg-attachments.html">AWS Direct Connect Gateways</a>, <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-peering.html">Transit Gateways from other Regions</a>, and <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-connect.html">Transit Gateway Connect peers</a>.

Among these various attachments, VPN, AWS Direct Connect Gateway and Transit Gateway Connect peers have quotas on the number of prefixes that are advertised, both to and from Transit Gateway. Along with attachment-specific quotas, each Transit Gateway has a quota on the total number of routes. These attachment quotas, along with VPC and Transit Gateway peer attachments routes, contribute towards the overall quota. You can learn more about the quotas by referring to the <a href="https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html">Transit Gateway quotas</a> section of our documentation.

As the number of attachments increases over time, monitoring these quotas from within the AWS Management Console or the Command Line Interface (CLI) becomes complex.  In this blog, we walk through a serverless solution to monitor Transit Gateway attachments and send alerts on the corresponding route limits. This solution uses <a href="https://aws.amazon.com/cloudwatch/">Amazon CloudWatch</a>, <a href="https://aws.amazon.com/transit-gateway/network-manager/">Transit Gateway Network Manager</a>, <a href="https://aws.amazon.com/lambda/">AWS Lambda</a> and <a href="https://aws.amazon.com/dynamodb/">Amazon DynamoDB</a>.

<strong>Solution architecture:</strong>

![](/TGWRouteMonitoring.jpg)

<strong>Solution overview:</strong>

When deployed, this solution captures the current state of the Transit Gateways in your account within a given Region. This initial state is captured by triggering an AWS Lambda function, and the state information is written to a DynamoDB table. Next, the solution listens for routing update events sent by <a href="https://aws.amazon.com/transit-gateway/network-manager">Transit Gateway Network Manager</a> to CloudWatch Logs. Any such events invokes another Lambda function to update the DynamoDB table.

The solution also deploys a Lambda function, which runs every minute, to scan the DynamoDB table and calculate the number of prefixes advertised to and from each attachment. It does this for every Transit Gateway in your account in a given Region. As this information is processed, the Lambda function pushes the metrics to CloudWatch using the custom metric push API.

You use these metrics to create CloudWatch dashboards and alerts based on the limits for each attachment type by following the instructions for <a href="https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html">Creating a CloudWatch alarm based on a static threshold</a> in our documentation.

<strong>Prerequisites</strong>

Readers of this blog post should be familiar with the following AWS services:
<ul>
 	<li><a href="https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html">Transit Gateway</a></li>
 	<li><a href="https://docs.aws.amazon.com/vpc/latest/tgw/how-network-manager-works.html">Transit Gateway Network Manager</a></li>
 	<li><a href="https://aws.amazon.com/cloudformation/">AWS CloudFormation</a></li>
 	<li><a href="https://aws.amazon.com/lambda/">AWS Lambda</a></li>
 	<li><a href="https://aws.amazon.com/cloudwatch/">Amazon CloudWatch</a></li>
 	<li><a href="https://aws.amazon.com/dynamodb/">Amazon DynamoDB</a></li>
 	<li><a href="https://aws.amazon.com/s3/">Amazon S3</a></li>
</ul>
For this walkthrough, you should have the following:
<ul>
 	<li>An <a href="https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/">AWS Account</a>, you can also create a <a href="https://aws.amazon.com/free">free tier</a> account here.</li>
 	<li>AWS Command Line Interface (AWS CLI): You need the <a href="https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html">AWS CLI installed</a> and <a href="https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html">configured</a> on your workstation.</li>
 	<li>Credentials configured in the AWS CLI should have the below permissions:
<ul>
 	<li>Amazon S3 full access to allow create, delete buckets and upload objects. <a href="https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonS3FullAccess">Here</a> is an example policy that you can tweak to your needs.</li>
 	<li>CloudFormation full access to allow create, delete, and describe stacks. <a href="https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AWSCloudFormationFullAccess">Here</a> is an example policy that you can tweak to your needs.</li>
 	<li>Lambda full access to create, delete, update, and run Lambda functions. <a href="policy/AWSLambda_FullAccess">Here</a> is an example policy that you can tweak to your needs.</li>
</ul>
</li>
 	<li>Transit Gateway Network Manager is a global service and uses CloudWatch in the us-west-2 Region for event processing. Therefore, this solution must be deployed in us-west-2. However, the solution can monitor Transit Gateways in any Region.
<ul>
 	<li>Make sure that you deploy the solution in the us-west-2 Region and your AWS CLI default Region is us-west-2. If us-west-2 is not the default Region, reference the Region explicitly while running AWS CLI commands using --region us-west-2 switch.</li>
</ul>
</li>
 	<li>Amazon S3 bucket in the us-west-2 Region for staging Lambda deploy packages.</li>
 	<li>Amazon S3 buckets in every Region where you must monitor the route limits of Transit Gateways.</li>
 	<li>One or more Transit Gateways with attachments and route tables configured.</li>
 	<li>Transit Gateway Network Manager should be configured to monitor all Transit Gateways in your account.</li>
</ul>
<strong>Walk through:</strong>
<ol>
 	<li>Create an Amazon S3 bucket in us-west-2 for staging the deployment packages. <em><em>Note: You must specify LocationConstraint for every Region other than us-east-1.</em></em>
<pre><code class="lang-bash">•	aws s3api create-bucket --bucket <span style="color: #ff0000;">&lt;bucket-name&gt;</span> --Region us-west-2 --create-bucket-configuration LocationConstraint=us-west-2</code></pre>
</li>
 	<li>Create an Amazon S3 bucket in the Region where the Transit Gateway you are planning to monitor is present. For example, this snippet created the bucket in us-east-1<code></code>
<pre><code class="lang-bash">•	aws s3api create-bucket --bucket <span style="color: #ff0000;">&lt;bucket-name&gt;</span> --Region us-east-1 </code></pre>
</li>
 	<li>Download and unzip the file containing the CloudFormation template and Lambda function code from <a href="https://github.com/aws-samples/how-to-monitor-tgw-route-limits-using-serverless-architecture/archive/refs/heads/main.zip">here</a>. This can also be done by running the command that follows to a directory in your local workstation. You must run all of the subsequent commands from this directory.
<pre><code class="lang-bash">$ wget https://github.com/aws-samples/how-to-monitor-tgw-route-limits-using-serverless-architecture/archive/refs/heads/main.zip
$ unzip main.zip
$ cd how-to-monitor-tgw-route-limits-using-serverless-architecture</code></pre>
</li>
 	<li>Zip the Lambda functions <code>init_lambda_function.py</code>, <code>update_lambda_function.py</code> and <code>put_metric_lambda_function.py</code> and upload it to an Amazon S3 bucket you created in step 1. <em><em>NOTE: zip command was executed on Mac OSX. Depending on your environment ‘zip’ command syntax might vary.</em></em>
<pre><code class="lang-bash">$ zip init_lambda_function.py.zip init_lambda_function.py
$ zip update_lambda_function.py.zip update_lambda_function.py
$ zip put_metric_lambda_function.py.zip put_metric_lambda_function.py
$ aws s3 cp init_lambda_function.py.zip s3://<span style="color: #ff0000;">&lt;bucket-name-from-step-1&gt;</span>/
$ aws s3 cp update_lambda_function.py.zip s3://<span style="color: #ff0000;">&lt;bucket-name-from-step-1&gt;</span>/
$ aws s3 cp put_metric_lambda_function.py.zip s3://<span style="color: #ff0000;">&lt;bucket-name-from-step-1&gt;</span>/</code></pre>
</li>
 	<li>Create the resources required by deploying the AWS CloudFormation template and running the command that follows. You must provide the following information, and you can change the parameters based on your specific needs.
<ul>
 	<li><code>CloudWatchMetricNameSpace</code> is the <a href="https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#Namespace">CloudWatch metric namespace</a> under which all the route metrics will be pushed.</li>
 	<li><code>S3BucketWithDeploymentPackage</code>. Name of Amazon S3 bucket used in step 1. This will have the deployment package for all the Lambda functions used in this blog.</li>
 	<li><code>S3BucketForTGWRoutesExport</code>. Name of Amazon S3 bucket used in step 2. This will be used to store the route table exported to capture the initial state of Transit Gateways, its attachments and the number of routes in the route tables.</li>
 	<li><code>TGWRegion</code>. Region where the Transit Gateways you want to monitor are present.</li>
</ul>
</li>
</ol>
<pre style="padding-left: 40px;"><code class="lang-bash">$ aws cloudformation create-stack \
--stack-name <span style="color: #ff0000;">TgwRouteMonitoring</span> \
--template-body file://TGWRouteMonitoring.yaml \
--parameters ParameterKey=CloudWatchMetricNameSpace,ParameterValue=<span style="color: #ff0000;">TGWRoutes</span>
 ParameterKey=S3BucketWithDeploymentPackage,ParameterValue=<span style="color: #ff0000;">&lt;bucket-name-from-step-1&gt;</span> ParameterKey=S3BucketForTGWRoutesExport,ParameterValue=<span style="color: #ff0000;">&lt;bucket-name-from-step-2&gt;</span> ParameterKey=TGWRegion,ParameterValue=<span style="color: #ff0000;">&lt;Region-of-tgw-you-want-to-monitor&gt;</span> \
--capabilities CAPABILITY_IAM \
--Region us-west-2
</code></pre>
<p style="padding-left: 40px;">This stack includes resources that affect permissions in your AWS account by creating necessary IAM roles. You must explicitly acknowledge this by specifying CAPABILITY_IAM or CAPABILITY_NAMED_IAM value for the –capabilities parameter.</p>
Stack creation will take you approximately 5–7 minutes. Check the status of the stack by running the command that follows every few minutes. You should see StackStatus value as CREATE_COMPLETE when done.

Example:
<pre><code class="lang-bash">aws cloudformation describe-stacks --stack-name <span style="color: #ff0000;">TgwRouteMonitoring</span> | grep StackStatus</code></pre>
The CloudFormation template will create the following resources:
<ul>
 	<li>Two Amazon DynamoDB tables (Logical ID: <code>RoutesDDBTableIn</code> and <code>RoutesDDBTableOut</code>) with 5 Read and Write Capacity Units (RCU and WCU), used to store all the required parameters to monitor the number of routes. It also creates Write Scaling Policy for Amazon DynamoDB to scale the WCUs to max of 15.</li>
 	<li>InitLambdaFunction (<code>init_lambda_function.py</code>) with required IAM permissions to export Transit Gateway routes and populate the DynamoDB Tables.</li>
 	<li>UpdateLambdaFunction (<code>update_lambda_function.py</code>) with required IAM permissions to track Transit Gateway route install and uninstall events and update the DynamoDB tables accordingly.</li>
 	<li>PutMetricLambdaFunction (<code>put_metric_lambda_function.py</code>) with required IAM permissions to scan the DynamoDB table, calculate per attachment incoming and outgoing route advertisements and then push the metrics to CloudWatch.</li>
 	<li>CloudWatch event rule to run UpdateLambdaFunction as and when there is a Transit Gateway route install and uninstall event.</li>
 	<li>CloudWatch schedule rule with required IAM permissions to invoke PutMetricLambdaFunction every minute. This will scan the DynamoDB table, calculate per attachment incoming and outgoing route advertisements and then push the metrics to CloudWatch.</li>
 	<li>CloudWatch schedule rule with required IAM permissions to invoke InitLambdaFunction every 60 minutes. This function will export the routes in Transit Gateway route tables to an Amazon S3 bucket and then parse the data and update the DynamoDB table.</li>
</ul>
Once the stack is deployed, we must populate the DynamoDB table with the current state of Transit Gateways and route tables. We do that by invoking the InitLambdaFunction manually from AWS CLI. We need the physical ID of the function to do this. That is also done by describing the AWS CloudFormation template as shown in the following snippet:
<pre><code class="lang-bash">$ aws cloudformation describe-stack-resources --stack-name <span style="color: #ff0000;">TgwRouteMonitoring</span> --Region us-west-2 | grep <span style="color: #ff0000;">InitLambdaFunction</span>.

"PhysicalResourceId": "<span style="color: #ff0000;">TGWRTMON-InitLambdaFunction-1E4ONARQ02SM3</span>", 
"LogicalResourceId": "InitLambdaFunction"
</code></pre>
Use the value of PhysicalResourceId from the above output and invoke the function using the following command:

<code class="lang-bash">$ aws lambda invoke --function-name <span style="color: #ff0000;">TGWRTMON-InitLambdaFunction-1E4ONARQ02SM3</span> response.json --Region us-west-2
</code>

Once the function has been invoked, you should see the following output:
<pre><code class="lang-bash">{
    "ExecutedVersion": "$LATEST", 
    "StatusCode": 200
}
</code></pre>
At this point, all the required components are in place to monitor the number of routes per attachment per Transit Gateway. InitLambdaFunction has populated the DynamoDB table, UpdateLambdaFunction are triggered as and when there is a Transit Gateway route install or uninstall event, and PutMetricLambda is calculating the routes per attachment every minute and pushing it to CloudWatch.

To view the metrics in the AWS Management Console, navigate to CloudWatch, then go to Metrics and click on the Custom Namespace created by the PutMetricLambdaFunction.

![](/Cloudwatch1.png)

&nbsp;

Under namespace, you find the Metrics for each attachment depicted by its attachment-id, click on the desired Metric.

![](/Cloudwatch2.png)

&nbsp;

Under each Metric are its corresponding dimensions (IN or OUT). Click on the desired dimension.

<em>NOTE: For VPC and Transit Gateway Peering attachments, ‘IN’ and ‘OUT’ means the number of prefixes accessible in each direction. For example for VPC attachments, IN indicates the number of prefixes in the VPC reachable from TGW perspective. Dimension ‘OUT’ for VPC attachments indicates how many prefixes are reachable from the VPC via TGW.</em>

![](/Cloudwatch3.png)

<em> </em>

Useful statistic for these metrics is ‘custom percentile, p100’ for a period of 1 minute.

![](/Cloudwatch4.png)

You use these metrics to create dashboards and alerts based on the quotas for each individual attachment, by following the instructions in <a href="https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html">CloudWatch documentation</a>.

<strong>Cost of the solution:</strong>

Cost will depend on how many route update events are generated in your network and processed, stored by the solution. More information on pricing can be found on public pricing pages for each of the services:
<ul>
 	<li><a href="https://aws.amazon.com/dynamodb/pricing/">Amazon DynamoDB pricing</a></li>
 	<li><a href="https://aws.amazon.com/lambda/pricing/">AWS Lambda pricing</a></li>
 	<li><a href="https://aws.amazon.com/s3/pricing/">Amazon S3 pricing</a></li>
 	<li><a href="https://aws.amazon.com/cloudwatch/pricing/">Amazon CloudWatch pricing</a></li>
</ul>
<strong>Clean up:</strong>

To ensure that no charges are incurred, be sure to empty and delete the Amazon S3 bucket created in step 1 and 2, and delete the CloudFormation stack created in step 5.

<strong>Conclusion:</strong>

In this blog post, we demonstrated how to monitor the number of routes to each Transit Gateway by deploying a serverless solution and using CloudWatch. You can use these metrics to create alarms in CloudWatch to get notified when the number of routes are approaching its attachment limit and take action to keep the routes within limits.

&nbsp;
