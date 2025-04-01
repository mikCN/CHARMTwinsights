import json
import requests
import os
import charmtwinsights

#if the hapi fhir JPA server has a different address, change this line:
hapi_fhir_server = "http://localhost:8080"


def submit_json_to_fhir(file_path):

    with open(file_path, 'r') as f:
        json_data = json.load(f)

    # For Bundles, submit to the root endpoint
    # For individual resources, submit to the resource-specific endpoint
    if json_data.get('resourceType') == 'Bundle':
        url = f'{hapi_fhir_server}/fhir/'

    else:
        resource_type = json_data.get('resourceType')
        url = f'{hapi_fhir_server}/fhir/{resource_type}'
        
    headers = {
        'Content-Type': 'application/fhir+json',
        'Accept': 'application/fhir+json'
    }
    
    print(f"\nSubmitting to: {url}")
    response = requests.post(url, json=json_data, headers=headers)
    return response

def process_directory(directory_path):
    filenames = os.listdir(directory_path)

    # filenames that start with hospitalInformation or practitionerInformation must be processed first, if they exist

    metadata_files = [filename for filename in filenames if filename.startswith('hospitalInformation') or filename.startswith('practitionerInformation')]
    other_files = [filename for filename in filenames if filename not in metadata_files]
    filenames = metadata_files + other_files
    
    for filename in filenames:
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            print(file_path)
            resp = submit_json_to_fhir(file_path)
            if resp.status_code in [200, 201]:
                print(f'\nSuccessfully uploaded {filename}: Status {resp.status_code}')
            else:
                print(f'\nError uploading {filename}: Status code {resp.status_code}')



patients_directory_path = './synthea/output/fhir'
process_directory(patients_directory_path)
