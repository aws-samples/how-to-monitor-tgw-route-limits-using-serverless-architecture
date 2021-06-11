<a href="https://aws.amazon.com/transit-gateway/">AWS Transit Gateway</a> simplifies your network and puts an end to complex peering relationships. It acts as a cloud router and scales elastically based on the volume of network traffic. It can centralize connections (known as attachments) from your on-premises networks, and attach to <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html">Amazon Virtual Private Clouds (VPC)</a> <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpn-attachments.html">Virtual Private Networks (VPN)</a>, <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-dcg-attachments.html">AWS Direct Connect Gateways</a>, <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-peering.html">Transit Gateways from other Regions</a>, and <a href="https://docs.aws.amazon.com/vpc/latest/tgw/tgw-connect.html">Transit Gateway Connect peers</a>.

Among these various attachments, VPN, AWS Direct Connect Gateway and Transit Gateway Connect peers have quotas on the number of prefixes that are advertised, both to and from Transit Gateway. Along with attachment-specific quotas, each Transit Gateway has a quota on the total number of routes. These attachment quotas, along with VPC and Transit Gateway peer attachments routes, contribute towards the overall quota. You can learn more about the quotas by referring to the <a href="https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html">Transit Gateway quotas</a> section of our documentation.

As the number of attachments increases over time, monitoring these quotas from within the AWS Management Console or the Command Line Interface (CLI) becomes complex.  In this blog, we walk you through a serverless solution to monitor Transit Gateway attachments and send alerts on the corresponding route limits. This solution uses <a href="https://aws.amazon.com/cloudwatch/">Amazon CloudWatch</a>, <a href="https://aws.amazon.com/transit-gateway/network-manager/">Transit Gateway Network Manager</a>, <a href="https://aws.amazon.com/lambda/">AWS Lambda</a> and <a href="https://aws.amazon.com/dynamodb/">Amazon DynamoDB</a>.

<strong>Solution architecture:</strong>

![](/TGWRouteMonitoring.jpg)

Details of solution and implementation steps can be found in <a href="https://aws.amazon.com/blogs/networking-and-content-delivery/monitoring-aws-transit-gateway-route-limits-using-a-serverless-architecture/">this blog post.</a>


