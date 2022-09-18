"""
Functions used to send data about members to cloud-lines
"""
import requests


def add_cloud_lines_member(cloud_lines_account, member):
    """
    inform cloud-lines account of the added member by sending a POST request

    @param cloud_lines_account: (str) the domain of the clouod-lines account - used to form the url to send requests to
    @param member: (Member) the new member whose details are to be sent to cloud-lines
    """
    
    data = {
        "user": {
            "email": member.user_account.email,
            "username": member.user_account.email,
            "first_name": member.user_account.first_name,
            "last_name": member.user_account.last_name,
        },
        "phone": member.contact_number,
        "member_type": "read_only",
    }
    print(data)
    response = requests.post(f"{cloud_lines_account}/api/memberships", json=data)
    print(response)
