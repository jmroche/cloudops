"""
This is an application to scrape New Jersey's DMV office looking for appointments for 
Out of state license transfer and let me know once it founds one available and the next available date
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys
import boto3
import os

# Link to the NJ DMV out of state license transfer site 
NJ_URL = "https://telegov.njportal.com/njmvc/AppointmentWizard/7"
# This is the id of th element containing the appoitnment information for North Bergen
# If another city needs to be sselected lookup their id
# For example. Bayonne, NJ, the Id of the span element would be: dateText477
nj_city_id= "dateText577"
CITY = "North Bergen"


# ************** TEST SITE WITH AVAILABLE APPOINTMENTS **************
test_url = "https://telegov.njportal.com/njmvc/AppointmentWizard/6"
test_id = "dateText76"
# ************** TEST SITE WITH AVAILABLE APPOINTMENTS **************



def send_sns_message(message:str):
    """
    Function to send appoitnment information with AWS SNS service.
    First it will getthe topic name from SSM Parameter store and 
    then publish the message. The Parameter is created from the CDK project,
    where the topic and subscription is created. Subscription email needs
    to be modified there.
    """
    # running_on_fargate = os.getenv("0")

    # if running_on_fargate == "FARGATE":
    sns_client = boto3.client("sns")
    ssm = boto3.client("ssm")
    ssm_response = ssm.get_parameter(
        Name="sns-topic-arn",
        WithDecryption=True
    )
    sns_topic = ssm_response["Parameter"]["Value"]

    sns_publish = sns_client.publish(
        TopicArn=sns_topic,
        Message=message,
        Subject="DMV License Appointmet Status Checker"
    )
    print(sns_publish)

print(f"Environment Variable: {os.getenv('0')}")

# Check in what platform we are running
# The Docker environment installs the driver for Linux,
# but I'm using the drivers added here, in order to use it
# and test on deffierent OS. 
# This could be optimized and reduced image size if only will run on Linux env.
os = sys.platform

if os == "darwin":
    driver_path = "./chromedriver_mac"
elif os == "linux":
    driver_path = "./chromedriver_linux"
elif os == "win32":
    driver_path = "./chromedriver.exe"


# Set the chrome options for the driver 
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--single-process')
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--hide-scrollbars')
chrome_options.add_argument("--disable-dev-shm-usage")

# Create the driver and call the get method to laod the URL
driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
driver.implicitly_wait(30)
driver.get(NJ_URL)

# Search for the element containign the appointments for North Bergen
search_appointments = driver.find_element_by_id(nj_city_id).text

# Convert string to List and get first element
number_apps_available = search_appointments.split(" ")[0]

# If first element is No, then there are no appointments
# If yes convert to int and print the appointmet info and link to book
 
if number_apps_available != "No":
    number_apps_available = int(number_apps_available)
    apps_split = search_appointments.replace("\n", " ").split(" ")[3::]
    message = f"{number_apps_available} appointments found in {CITY}!\n{''.join(apps_split)}\nHere's the link to book: https://telegov.njportal.com/njmvc/AppointmentWizard/7/57"
    send_sns_message(message=message)
    # print(f"{number_apps_available} appointments found in North Bergen!")
    # print(" ".join(apps_split))
    # print("Here's the link to book: https://telegov.njportal.com/njmvc/AppointmentWizard/7/57")

else:
    print("No appoitnments available at this time")

# print(number_apps_available)

driver.close()

