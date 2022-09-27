"""
Script that will compare Service Quotas against various AWS accounts.
The script will accept various account profiles as stored in .aws/config on the local machine
and get the compare the quotas for a set of services provided for the accounts provided. 
"""

import boto3
import click


# TODO: Complete Click arguments
# TODO: Create logic for boto session
# TODO: Generate list of services if user doesn't provide a service to analyze
# TODO: Create logic to compare quotas for services provided and generate a result 

@click.command()
@click.option(
    "--accounts", "-a",
    help="AWS Account profiles to use. By default only default profile will be used",
    nargs=2,
    type=str,
    required=True
)
@click.option(
    "--service", "-s",
    help="AWS Service Quota service code to be evaluated (e.g., 'ec2').",
    type=str,
    default=None,
    required=False
)
def cli(accounts):
    click.echo(list(accounts))

client = boto3.client("service-quotas")


def list_services() -> list:
    """Calls AWS Service Quotas API and returns a list of services available to verify quotas.

    Returns:
        List: Returns a list of dictionaries containing the Service Code and Service Name
        Example: {'ServiceCode': 'AWSCloudMap', 'ServiceName': 'AWS Cloud Map'}
    """
    response = client.list_services(
        MaxResults=100
    )

    services = response["Services"]

    # print(len(services))

    while "NextToken" in response:
        response = client.list_services(
            MaxResults = 100,
            NextToken = response["NextToken"]
        )
        services += response

    # print(len(services))

    return services




def list_service_quotas(services: dict) -> list:
    """Given a service or a dict of services  grab the quotas for the service from AWS Service Quotas API

    Args:
        services (str or dict): Pass a single service or list of dictionaries with services

    Returns:
        list: Returns a list with Quotas for the service(s)
    """
    
    # Check the type of the input. If not str or list return an error

    if isinstance(services, dict):

    # List service quotas for services

        service_quotas_response = client.list_service_quotas(
            ServiceCode=services["ServiceCode"],
            MaxResults = 100
        )
        service_quotas = service_quotas_response["Quotas"]
        print(len(service_quotas))

        while "NextToken" in service_quotas_response:
            service_quotas_response = client.list_service_quotas(
                ServiceCode = services["ServiceCode"],
                MaxResults = 100,
                NextToken = service_quotas_response["NextToken"]
            )

            service_quotas += service_quotas_response

        return service_quotas
    else:
        raise TypeError("The function only accepts a dictionary object as an argument.")



if __name__ == '__main__':
    cli()


        
