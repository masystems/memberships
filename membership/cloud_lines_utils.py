"""
Functions used to send data about members to cloud-lines
"""
import requests


def add_cloud_lines_member(cloud_lines_account, member):
    """
    Inform cloud-lines account of the added member by sending a POST request.

    @param cloud_lines_account: (str) the domain of the clouod-lines account - used to form the url to send requests to
    @param member: (Member) the new member whose details are to be sent to cloud-lines
    """
    
    data = {
        "email": member.user_account.email,
        "username": member.user_account.email,
        "first_name": member.user_account.first_name,
        "last_name": member.user_account.last_name,
        "phone": member.contact_number,
        "member_type": "read_only",
    }
    response = requests.post(f"{cloud_lines_account}/api/memberships", json=data)

def edit_cloud_lines_member(cloud_lines_account, member, old_member):
    """
    Inform cloud-lines account of the edited member by sending a PATCH request.
    The data sent are:
        1. the key (to be used to get the user which has been edited)
        2. the changes (new values the changed fields)

    @param cloud_lines_account: (str) the domain of the clouod-lines account - used to form the url to send requests to
    @param member: (Member) the new member whose details are to be sent to cloud-lines
    @param changes: (dict) the details of the member before it was changed
    """

    changes = {}

    # for each field that has changed, get the new value
    if old_member["first_name"] != member.user_account.first_name:
        changes.update({"first_name": member.user_account.first_name})
    if old_member["last_name"] != member.user_account.last_name:
        changes.update({"last_name": member.user_account.last_name})
    if old_member["phone"] != member.contact_number:
        changes.update({"phone": member.contact_number})

    if len(changes) > 0:
        data = {
            "key": {
                "username": member.user_account.email
            },
            "changes": changes
        }
        response = requests.patch(f"{cloud_lines_account}/api/memberships", json=data)
