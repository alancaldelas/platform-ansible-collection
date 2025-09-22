#!/usr/bin/python
# plugins/modules/redfish_iso_mount.py

DOCUMENTATION = r'''
---
module: redfish_iso_mount
short_description: Mount ISO via Redfish virtual media
description:
  - Mount ISO images to servers using Redfish virtual media
options:
  baseuri:
    required: true
    description: Base URI of Redfish service
  username:
    required: true
    description: User for Redfish authentication
  password:
    required: true
    description: Password for Redfish authentication
  image_url:
    required: true
    description: URL of ISO image to mount
  media_type:
    default: CD
    description: Type of media (CD/DVD)
'''

from ansible.module_utils.basic import AnsibleModule
import requests
import json

def main():
    module = AnsibleModule(
        argument_spec=dict(
            baseuri=dict(required=True, type='str'),
            username=dict(required=True, type='str'),
            password=dict(required=True, type='str', no_log=True),
            image_url=dict(required=True, type='str'),
            media_type=dict(default='CD', type='str'),
            inserted=dict(default=True, type='bool'),
            write_protected=dict(default=True, type='bool')
        )
    )

    baseuri = module.params['baseuri']
    username = module.params['username']
    password = module.params['password']
    image_url = module.params['image_url']

    # Redfish virtual media endpoint
    virtual_media_url = f"https://{baseuri}/redfish/v1/Managers/1/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia"
    
    payload = {
        "Image": image_url,
        "Inserted": module.params['inserted'],
        "WriteProtected": module.params['write_protected']
    }

    try:
        response = requests.post(
            virtual_media_url,
            auth=(username, password),
            json=payload,
            verify=False,
            timeout=30
        )
        
        if response.status_code in [200, 201, 202, 204]:
            module.exit_json(
                changed=True,
                msg=f"ISO mounted successfully from {image_url}"
            )
        else:
            module.fail_json(
                msg=f"Failed to mount ISO: {response.status_code} - {response.text}"
            )
            
    except Exception as e:
        module.fail_json(msg=f"Error mounting ISO: {str(e)}")

if __name__ == '__main__':
    main()
