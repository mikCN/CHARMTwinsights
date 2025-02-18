

import json
import requests
import os

#if the hapi fhir JPA server has a different address, change this line:
hapi_fhir_server = "http://localhost:8080/fhir/"


def submit_json_to_fhir(file_path):
    with open(file_path, 'r') as f:
        json_data = json.load(f)
    
    # For Bundles, submit to the root endpoint
    # For individual resources, submit to the resource-specific endpoint
    if json_data.get('resourceType') == 'Bundle':
        url = hapi_fhir_server
    else:
        resource_type = json_data.get('resourceType')
        url = f'{hapi_fhir_server}/{resource_type}'
    
    headers = {
        'Content-Type': 'application/fhir+json',
        'Accept': 'application/fhir+json'
    }
    
    print(f"\nSubmitting to: {url}")
    response = requests.post(url, json=json_data, headers=headers)
    return response

def process_directory(directory_path):
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            print(file_path)
            resp = submit_json_to_fhir(file_path)
            if resp.status_code in [200, 201]:
                print(f'\nSuccessfully uploaded {filename}: Status {resp.status_code}')
            else:
                print(f'\nError uploading {filename}: Status code {resp.status_code}')


metadata_directory_path = './Downloads/synthea_output/metadata'
patients_directory_path = './Downloads/synthea_output/fhir'
process_directory(metadata_directory_path)
process_directory(patients_directory_path)
