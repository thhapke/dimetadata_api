########################################################
#### Using SAP Data Intelligence API Business Hub
#### Doc: https://api.sap.com/api/metadata/resource
########################################################
import logging
import sys

import requests
import json
import yaml


# Get containers - result is stored in argument
def get_containers(connection, parent_container=None, container_filter=None):
    if not parent_container:
        parent_container = {
            "id": "connectionRoot",
            "name": "Root",
            "qualifiedName": "/",
            "catalogObjectType": "ROOT_FOLDER"
        }

    logging.info(f"Get sub-container of {parent_container['name']}")
    restapi = f"/api/v1/catalog/containers/{parent_container['id']}/children"
    url = connection['url'] + restapi
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    params = {"containerId": parent_container['id'], "$filter": container_filter}
    r = requests.get(url, headers=headers, auth=connection['auth'], params=params)

    response = json.loads(r.text)
    if r.status_code != 200:
        logging.error("Get containers: {}".format(response['message']))
        return None

    parent_container["containers"] = response["containers"]

    for container in parent_container["containers"]:
        get_containers(connection=connection, parent_container=container, filter=filter)

    return parent_container


def get_datasets(connection, parent_container):
    restapi = f"/api/v1/catalog/containers/{parent_container['id']}/children"
    url = connection['url'] + restapi
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    params = {"containerId": parent_container['id'], "type": "DATASET"}
    r = requests.get(url, headers=headers, auth=connection['auth'], params=params)

    response = json.loads(r.text)
    if r.status_code != 200:
        logging.error("Get containers: {}".format(response['message']))

    return response


def get_container_by_name(parent_container, qualified_name):
    c_found = None
    for c in parent_container["containers"]:
        qname = c['qualifiedName']
        if c['qualifiedName'] == qualified_name:
            c_found = c
            break
        if c['qualifiedName'] in qualified_name and len(c['containers']) > 0:
            c_found = get_container_by_name(c, qualified_name)
            if c_found:
                break
    return c_found


#########
# MAIN
########
if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    with open('../config.yaml') as yamls:
        config_params = yaml.safe_load(yamls)

    conn = {'url': config_params['url'],
            'auth': (config_params['tenant'] + '\\' + config_params['user'], config_params['password'])}
    data_directory = config_params['data_directory']

    # connection_id = "DI_DATA_LAKE"
    # EU_path = '/shared/catalog/EU/Population and society/Population structure 2020/'
    # EU_file = 'Budget structure 2020-4.csv'
    # qualified_name = EU_path + EU_file

    # filter ='name eq \'EU\''
    filter = None
    containers = get_containers(connection=conn, filter=filter)
    if not containers:
        logging.error("No container found!")
        sys.exit(1)
    print(json.dumps(containers, indent=4))
    qualified_name = "/DI_DATA_LAKE/shared"
    container = get_container_by_name(containers, qualified_name)
    if container:
        datasets = get_datasets(connection=conn, parent_container=container)
        print(json.dumps(datasets, indent=4))
    else:
        logging.error((f"Dataset not found by name: {qualified_name}"))
