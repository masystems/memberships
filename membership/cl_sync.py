"""
Functions used to send data about members to cloud-lines
"""

import requests
import sys
from json import loads, dumps
from requests.auth import HTTPBasicAuth

from membership.models import MembershipSubscription


def add_or_edit_user_on_cl(subscription):
    # membership_package = MembershipPackage.objects.get(organisation_name='Test Org2')
    # member = MembershipSubscription.objects.first()
    ## create header
    headers = {'Content-Type': 'application/json'}
    data = {'token': f'{subscription.membership_package.cloud_lines_token}',
            'email': f'{subscription.member.user_account.email}',
            'username': f'{subscription.member.user_account.email.strip().replace(" ", "").lower()}',
            'first_name': f'{subscription.member.user_account.first_name}',
            'last_name': f'{subscription.member.user_account.last_name}',
            'phone': f'{subscription.member.contact_number}',
            'permission_level': 'read_only_users'}
    post_res = requests.post(url=f'{subscription.membership_package.cloud_lines_domain}/api/membership-add-edit-user',
                             headers=headers,
                             data=dumps(data))

    if post_res.status_code == 403:
        # permission denied
        print(post_res.json()['detail'])
    elif post_res.status_code == 200:
        # all good
        print(post_res.json())



def delete_cloud_lines_member(member, cloud_lines_account):
    """
    @param member: (Member) the member whose membership subscription has been deleted.
    @param membership_package: (str) the url of the cloud-lines account to delete the member from.
    """

    data = {"username": member.user_account.email}
    response = requests.delete(f"{cloud_lines_account}/api/memberships/", json=data)


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