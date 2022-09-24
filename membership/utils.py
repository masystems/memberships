"""
Functions used to send data about members to cloud-lines
"""
import requests

from membership.models import MembershipSubscription


def add_cloud_lines_member(cloud_lines_account, member, member_type="read_only"):
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
        "member_type": member_type,
    }
    response = requests.post(f"{cloud_lines_account}/api/memberships", json=data)

def edit_cloud_lines_member(cloud_lines_account, member, old_member, member_type=None):
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
    if "first_name" in old_member and old_member["first_name"] != member.user_account.first_name:
        changes.update({"first_name": member.user_account.first_name})
    if "last_name" in old_member and old_member["last_name"] != member.user_account.last_name:
        changes.update({"last_name": member.user_account.last_name})
    if "phone" in old_member and old_member["phone"] != member.contact_number:
        changes.update({"phone": member.contact_number})
    if "member_type" in old_member and old_member["member_type"] != member_type:
        changes.update({"member_type": member_type})

    if len(changes) > 0:
        data = {
            "key": {
                "username": member.user_account.email
            },
            "changes": changes
        }
        response = requests.patch(f"{cloud_lines_account}/api/memberships", json=data)

def delete_cloud_lines_member(member, cloud_lines_account):
    """
    @param member: (Member) the member whose membership subscription has been deleted.
    @param membership_package: (str) the url of the cloud-lines account to delete the member from.
    """

    data = {"username": member.user_account.email}
    response = requests.delete(f"{cloud_lines_account}/api/memberships", json=data)

def get_member_type(member, membership_package):
    """
    @param member: (Member) the member whose member type is to be retrieved.
    @param membership_package: (MembershipPackage) the membership_package which the member is associated with.
    """
    
    if member.user_account == membership_package.owner:
        return "owner"
    elif member.user_account in membership_package.admins.all():
        return "admin"
    elif MembershipSubscription.objects.filter(member=member).exists():
        return "read_only"
    else:
        return None
