
# Welcome to New Jersey's DMV Out Ff State License Appointment finder!

This project will scrape the New Jersey's DMV License site and look for appointments to perform an out of state license transfer. 
Once an appointment is found the subscribed user will receive an email with the details and link to book the appointment.

New Jersey's DMV Site for Out Of State Transfer: https://telegov.njportal.com/njmvc/AppointmentWizard/7

This projects uses `Selenium` to load the website and scrape it for a specific city and find available appoitnments.
The application is containerized and the build instructions can be found in `src/Dockerfile`.

The `cdk` directory contains the CDK project to build the container and deploy it to a Fargate scheduled task in AWS running every 10 minutes.
The cdk automation builds an AWS Virtual Private Cloud (VPC) with private subnets to place the Fargate task on an ECS cluster and pubic subnet to place a NAT Gateway. 
All the communication for the Fargate task is initiated by the task and directed outbound to the internet.

The CDK will create an ECR repository to save the built `Docker` image that will be deployed to AWS Fargate. Additionally, a SNS Topic and subscription will be created, and the information stored in SMS Parameter Store to be loaded from the main application source. As pointed in the instructions below, the subscriber needs to update their email the address in the `cdk.json` context configuration file. 

In order to run the project. Perform the following tasks:

* Ensure you have AWS CDK installed on your machine. Instructions found here: https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html 

* Ensure to have Docker installed on your machine. This is needed to build the image locally. Instructions found here: https://docs.docker.com/engine/install/ 

* Inside the `src` directory, find the `main.py` file, and modify the `nj_city_id` variable and update it with the id of the city you want search appointments for. 
  Example, Bayonne, NJ `id` is: dateText477. You can find this information by inspecting the New Jersey DMV website, and grabbing the `span id` for your preffered city.
  Additionally, change the global `CITY` variable with the name of the city (i.e. "North Bergen").

* Inside the `cdk` directory, find the `cdk.json` file and update the `email_address` variable with your email address. 

* Create a Python virtual environment, synthethize and deploy the application. Instructions below:

To manually create a virtualenv on MacOS and Linux. First change directory into `cdk` directory and perform the follwoing steps: 

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To deploy the project run:

```
$ cdk deploy
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
