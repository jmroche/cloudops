# Monitor EKS Managed Nodegroup AMI Releases with Python and Amazon EventBridge

## Automate the process of notifying yourself when a new version of the EKS Managed Nodegroup AMI is released.

**Introduction:**

The EKS Managed Nodegroup AMI is a pre-configured Amazon Machine Image (AMI) that can be used to create Amazon Elastic Kubernetes Service (EKS) managed node groups. Managed node groups are a great way to simplify the management of your EKS clusters, as AWS handles the provisioning, scaling, and maintenance of the nodes for you.

However, it can be difficult to keep track of when new versions of the EKS Managed Nodegroup AMI are released. This can be a problem, as new versions of the AMI often include security updates and bug fixes.

In this blog post, I will show you how to use Python and Amazon EventBridge to monitor an AWS official parameter in SSM Parameter store to notify when a new version of the EKS Managed Nodegroup AMI is released.

**Why monitor new versions of the AMI?**

There are a few reasons why you might want to monitor new versions of the EKS Managed Nodegroup AMI:

* To ensure that your EKS clusters are always up to date with the latest security updates and bug fixes.
* To take advantage of new features and functionality that have been added to the AMI.
* To improve the performance and reliability of your EKS clusters.

**How can you monitor new versions of the AMI?**

There are a few different ways that you can monitor new versions of the EKS Managed Nodegroup AMI:

* **Manually:** You can manually check the AWS documentation or the AWS blog to see if a new version of the AMI has been released.
* **Use a third-party tool:** There are a number of third-party tools that can help you monitor new versions of the AMI.
* **Use Python and Amazon EventBridge:** In this blog post, I will show you how to use Python, Amazon Simple Notification Service (SNS) and Amazon EventBridge to monitor new versions of the AMI.

**How to use Python and Amazon EventBridge to monitor new versions of the AMI**

To use Python and Amazon EventBridge to monitor new versions of the AMI, you will need to do the following:

1. Install the `boto3` library.
2. Create a `sns` client object.
3. Get the ARN of the parameter that stores the latest version of the EKS Managed Nodegroup AMI.
4. Create an EventBridge event.
5. Put the event into EventBridge.
6. Handle the event.

**The importance of automation**

Automation is important for a number of reasons. It can help you to save time, improve efficiency, and reduce errors. In the case of monitoring new versions of the EKS Managed Nodegroup AMI, automation can help you to ensure that your EKS clusters are always up to date with the latest security updates and bug fixes. This can help to protect your data and improve the performance of your clusters.