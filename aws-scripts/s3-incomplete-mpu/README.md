# Automating the creation of S3 Incomplete Multipart Upload Lifecycle Rules to Optimize Cost in AWS


This post will go over how you can use AWS Python SDK (Boto3) to scan and get all s3 bucket in an account, check its lifecycle policies, and create a lifecycle policy to delete incomplete multipart uploads if no lifecycle policy to do so exists.

 To understand what S3 Incomplete Multipart Uploads is, how to discover buckets that have incomplete MPUs with [S3 Storage Lens](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html) and how apply the lifecycle rules to these buckets manually, please check out this [post](https://aws.amazon.com/blogs/aws-cloud-financial-management/discovering-and-deleting-incomplete-multipart-uploads-to-lower-amazon-s3-costs/). 

Instead of doing it manually, my idea is to automate the updating of the lifecycle rule in all buckets for a given account using the [AWS Python SDK](https://aws.amazon.com/sdk-for-python/). Hopefully showing others how to use AWS SDK for Python and automation along the way.

At a high level, I want to get all the s3 buckets in a specific account and for each of these buckets apply a lifecycle configuration rule if none exists. Therefore, my first step is to get a list of all the buckets. To accomplish this, first I create an s3 client as shown below:

```
s3_client = boto3.client("s3")
```

The [S3 Client Class](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client) is a low-level representation of Amazon S3. The S3 client has a method called [list_buckets()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.list_buckets) that will return a dictionary with a list of all the buckets in that account. The Buckets dictionary within the response object contains this list of buckets. 

For this example, we are only interested in the bucket name, as that's the only required argument we need to add a lifecycle policy to an object. We save the response of the list_buckets() in a list object as follows:


```
buckets = []
buckets = s3_client.list_buckets()["Buckets"]
```

Now that we have a list of all buckets, we can iterate through the list and take an action, in our example we will check if this bucket has a lifecycle policy and if not then add one. We do this in two steps. 1) Check if to see if the policy exists and 2) Apply the policy. The logic for each of these steps is defined in two Python functions we will discuss later.

To iterate through the list will use a simple [for loop](https://docs.python.org/3/tutorial/controlflow.html#for-statements) and access the "Name" key of the Bucket object. We then use this bucket name as the argument to call the get_incomplete_mpu_policy() function to trigger the workflow.


```
for bucket_name in buckets:
    
    get_incomplete_mpu_policy(bucket=bucket_name["Name"])
```


The ```get_incomplete_mpu_policy()``` function is pretty simple. It will take the bucket name as its parameter and will check if this bucket has lifecycle policy rules in place. If there are no lifecycle rules in place, then it will call the ```create_incomplete_mpu_policy()``` function to create one. If there are lifecycle rules already present, then it will check if any of these rules have an explicit inclomplete mpu rule in place. If it finds there is an incomplete mpu rule, then it will just exit the function, and if there are none, then call the ```create_incomplete_mpu_policy()``` to create one.

This is just a simple implementation to demonstrate an idea. It's probably not the most efficient, nor the most [pythonic](https://docs.python-guide.org/writing/style/) way. For example, I probably could be using the [logging](https://docs.python.org/3/howto/logging.html#logging-howto) package to handle the output of the different checks to enhance observability by having well defined logs and outputs, among other things. I will probably update this script in the future, but for now, [printing](https://docs.python.org/3/library/functions.html#print) to [stdout](https://en.wikipedia.org/wiki/Standard_streams) should be enough to demonstrate the idea. 

Here's the complete function, we'll brake it down afterwards:


```
def get_incomplete_mpu_policy(bucket: str):
    """Given a bucket 'bucket' check if it has Lifecycle rules, in specific MPU Lifecycle rules. 
        If there aren't any Lifecycle rules create an MPU Lifecycle rule. If there are other
        Lifecycle rules, check first to ensure none of the rules is an MPU rule, by checking 
        if a rule with a statement 'AbortIncompleteMultipartUpload' exist.

    Args:
        bucket (str): bucket name to check and/or create rule.
    """

    # Check if there are lifecycle rules created on the bucket. Will return with ClientError if no rules configured on the bucket
    try:
        bucket_lifecycle = s3_client.get_bucket_lifecycle_configuration(
            Bucket=bucket
        )
    except ClientError:
        # This means there are no lifecycle rules for the bucket. Create one
        print(f"No Incomplete MPU rule exist for this bucket: {bucket}...Adding one")

        if not DRY_RUN:
            response = create_incomplete_mpu_policy(bucket=bucket)

            # If there's a response, the rule was created
            if response is not None:
                print(f"Lifecycle created for bucket {bucket}: \n{response}")
        else:
            print("No changes done...Running in Dry run mode")

    # If there are already Lifecycle rules create for the bucket, check if the rules contain an Incomplete MPU rule 
    else:
        print(f"Bucket {bucket} has already created Lifecycle Rules: \nChecking if there is an Incomplete MPU rule in place...")

        # Go through all the lifecycle rules configured in the bucket
        for rule in bucket_lifecycle["Rules"]:

            if rule.get("AbortIncompleteMultipartUpload"):
                print(f"The following Incomplete MPU rule already exist: {rule['ID']}. Nothing to do.")
            else:
                print(f"No Incomplete MPU rule exist for this bucket: {bucket}...Adding one")

                if not DRY_RUN:
                    response = create_incomplete_mpu_policy(bucket=bucket)
                    print(f"Incomplete MPU Lifecycle rule created for bucket {bucket}: \n{response}")
                else:
                    print(f"Not changing bucket {bucket}. Running in DRY RUN Mode")
```


Let's brake it down:


* First we define the [function](https://docs.python.org/3/glossary.html#term-function) and describe it's functionality by using [docstrings](https://peps.python.org/pep-0257/).



```
def get_incomplete_mpu_policy(bucket: str):
    """Given a bucket 'bucket' check if it has Lifecycle rules, in specific MPU Lifecycle rules. 
        If there aren't any Lifecycle rules create an MPU Lifecycle rule. If there are other
        Lifecycle rules, check first to ensure none of the rules is an MPU rule, by checking 
        if a rule with a statement 'AbortIncompleteMultipartUpload' exist.

    Args:
        bucket (str): bucket name to check and/or create rule.
    """
```

* Second, we check if there are lifecycle rules already configured for the bucket. To do this we use the s3 client method [get_bucket_lifecycle_configuration()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.get_bucket_lifecycle_configuration). This method will throw an exception of type ```ClientError```  if no rules are found, so we enclose the call in a try/except:

```
try:
    bucket_lifecycle = s3_client.get_bucket_lifecycle_configuration(
            Bucket=bucket
            )
except ClientError:
    # This means there are no lifecycle rules for the bucket. Create one
    print(f"No Incomplete MPU rule exist for this bucket: {bucket}...Adding one")
```

* If we get a ```ClientError``` then we know there are no lifecycle rules created. Next we check if we are running in dry mode or not. We do this by configuring a global variable as a [configuration toggle.](https://martinfowler.com/articles/feature-toggles.html)At the start of the script we declared the toggle as follows:

```
DRY_RUN = True
```

Setting ```DRY_RUN``` as ```True``` means we will perform all the checks, but will not apply any changes to the bucket. This is a good practice to test your script without risking impact to your production buckets.


```
if not DRY_RUN:
    response = create_incomplete_mpu_policy(bucket=bucket)

    # If there's a response, the rule was created
    if response is not None:
        print(f"Lifecycle created for bucket {bucket}: \n{response}")
    else:
        print("No changes done...Running in Dry run mode")
```

Here , if ```DRY_RUN``` is ```False``` we call the ```create_incomplete_mpu_policy()``` passing the ```bucket``` as the argument. We'll look at this function in a bit, but for now just know it will return the results of applying the lifecycle rule. Therefore, we check if this response is empty or not, and if not empty, the rule was created and we print the the response.


* If we don't get a ```ClientError``` then we know there are already lifecycle rules in place. Next, will go through all the rules created for this bucket to check if there is any rule containing the ```AbortIncompleteMultipartUpload``` statement. If no rule found, then no incomplete MPU rule exist and we create one, again by calling the ```create_incomplete_mpu_policy()``` function.  These rules are found inside ```bucket_lifecycle```  as defined earlier inside the try/except: 

```
bucket_lifecycle = s3_client.get_bucket_lifecycle_configuration(
            Bucket=bucket
        )
```

This is a list of dictionaries (each dictionary being a rule). We iterate through every rule and check if key ```AbortIncompleteMultipartUpload``` exists. If so, a rule containing the policy we need already exist and there's nothing do. Otherwise, we first check if we are running in ```DRY_RUN``` and if not, create the rule. This is done in the below code segment:


```
else:
        print(f"Bucket {bucket} has already created Lifecycle Rules: \nChecking if there is an Incomplete MPU rule in place...")

        # Go through all the lifecycle rules configured in the bucket
        for rule in bucket_lifecycle["Rules"]:

            if rule.get("AbortIncompleteMultipartUpload"):
                print(f"The following Incomplete MPU rule already exist: {rule['ID']}. Nothing to do.")
            else:
                print(f"No Incomplete MPU rule exist for this bucket: {bucket}...Adding one")

                if not DRY_RUN:
                    response = create_incomplete_mpu_policy(bucket=bucket)
                    print(f"Incomplete MPU Lifecycle rule created for bucket {bucket}: \n{response}")
                else:
                    print(f"Not changing bucket {bucket}. Running in DRY RUN Mode")
```

* As mentioned a few times already, we apply this rule to the bucket by calling the ```create_incomplete_mpu_policy()``` function and passing the bucket name we want to update as an argument. First, let's  take a look at the rule we want to apply:

```
rule = {
    "Rules": [
        {
            "ID": "delete-incomplete-mpu-7days",
            "Status": "Enabled",
            "Filter": {
                "Prefix": ""
            },
            "AbortIncompleteMultipartUpload": {
                "DaysAfterInitiation": 7
            }
        }
    ]
}
```

This rule defines the incomplete MPU rule policy, and sets these files to be deleted 7 days after created.


* We defined the create rules as follows:

```
def create_incomplete_mpu_policy(bucket: str) -> dict:
    """Function that calls the S3 API and puts a lifecycle configuration on the bucket passed to it
        and returns the lifecycle policy id to the caller

    Args:
        bucket (str): The name of the bucket to apply the configuration onto.

    Returns: 
        response (dict): Dictionary containing the information of the Lifecycle Rule created.
    """

    response = s3_client.put_bucket_lifecycle_configuration(
        Bucket = bucket,
        LifecycleConfiguration = rule
    )
    return response
```

Same as with the ```get_incomplete_mpu_policy()``` we define the function with its parameter and set the expected input and output [type hints](https://docs.python.org/3/library/typing.html#module-typing). Then, we provide a description of what the function does with a docstring. Afterwards, we do the actual work in the function; we call the ```put_bucket_lifecycle_configuration()``` method passing the bucket name and lifecycle rule we want to apply. Finally, we return the result of the action taken.

### Conclusion:

Hopefully this post provided a good example of how to use the **AWS SDK for Python (Boto3)** to automate some of the work of operating in AWS. There are a number of enhancements we could add to the script. For example, we could:

* Add logic to operate across multiple accounts
* Process multiple buckets in parallel using the [multiprocessing](https://docs.python.org/3/library/multiprocessing.html#module-multiprocessing) package
* Add [backoff and retry logic](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) in case the number of buckets are too large and you get throttled by calling the S3 API beyond the set limits.
* Many, many more...

One enhancement to increase the level of automation is to use event-driven architectures. With this approach, we could simply listen for events of a bucket being created. Once created, we can trigger a workflow to perform the logic described in this post. We can accomplish all this using event-driven and serverless architectures. The code for this is inside ```/s3-mpu-cdk``` directory, and I'll write a future post to explain how to use the ```AWS CDK``` to create  event-driven and serverless architectures using ```Amazon EventBridge``` and ```AWS Lambda```. 
