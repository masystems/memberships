from django.db import models
from django.contrib.auth.models import User


class MembershipPackage(models.Model):
    organisation_name = models.CharField(max_length=50)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='owner', verbose_name="Owner")
    admins = models.ManyToManyField(User, blank=True, related_name='admins', verbose_name="Admins")
    stripe_acct_id = models.CharField(max_length=255, blank=True)
    stripe_owner_id = models.CharField(max_length=255, blank=True)
    stripe_product_id = models.CharField(max_length=255, blank=True)

    BOLTONS = (
        ('none', 'None'),
        ('equine', 'Equine'),
    )
    bolton = models.CharField(max_length=12, choices=BOLTONS, null=True, default='none',
                              help_text="Boltons add additional fields to your member form.")
    cloud_lines_account = models.CharField(max_length=100, blank=True,
                                           help_text="Link your membership account to your cloud-lines account")
    enabled = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.organisation_name


class Price(models.Model):
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, related_name='pmembership_package', verbose_name="Membership Package")
    stripe_price_id = models.CharField(max_length=255, blank=True)
    nickname = models.CharField(max_length=255, blank=True)
    INTERVAL = (
        ('month', 'Monthly'),
        ('year', 'Yearly '),
    )
    interval = models.CharField(max_length=19, choices=INTERVAL, null=True, default='monthly',
                                      help_text="Payment frequency")
    amount = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=False)


class Member(models.Model):
    user_account = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=255, blank=True)
    county = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user_account.email


class MembershipSubscription(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='subscription', verbose_name="Membership Subscription")
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, related_name='membership_package', verbose_name="Membership Package")
    price = models.ForeignKey(Price, on_delete=models.CASCADE, blank=True, null=True, related_name='price', verbose_name="Price")
    stripe_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    validated = models.BooleanField(default=False)

    PAYMENT_TYPE = (
        ('card_payment', 'Card Payment'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque '),
        ('standing_order', 'Standing Order'),
        ('caf_standing_order', 'CAF standing Order'),
        ('petty_cash', 'Petty Cash'),
        ('bacs', 'BACS'),
        ('caf_voucher', 'Caf Voucher'),
        ('postal_cheque ', 'Postal Cheque'),
        ('paypal', 'Paypal')
    )
    payment_type = models.CharField(max_length=19, choices=PAYMENT_TYPE, null=True, default='card_payment',
                                    help_text="Payment type used by member")

    comments = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.membership_package.organisation_name


class Equine(models.Model):
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, blank=True, null=True, related_name='emembership_package', verbose_name="Equine Membership Package")
    subscription = models.ForeignKey(MembershipSubscription, on_delete=models.CASCADE, blank=True, null=True, related_name='esub', verbose_name="Equine Subscription")
    date_resigned = models.DateField(auto_now=True)
    gift_aid = models.BooleanField(default=False)
    signature_given_date = models.DateField(auto_now=False, blank=True, null=True)
    animal_owner = models.BooleanField(default=True)
    badge = models.BooleanField(default=True)
    joined = models.DateField(auto_now=True)
    expired = models.DateField(auto_now=False, blank=True, null=True)
    actual_renewal = models.DateField(auto_now=False, blank=True, null=True)
    do_not_mail = models.BooleanField(default=False)
    want_raffle_tickets = models.BooleanField(default=False)
    overseas = models.BooleanField(default=False)
    bad_address = models.BooleanField(default=False)
    returned_gdpr_date = models.DateField(auto_now=False, blank=True, null=True)
    gdpr_post = models.BooleanField(default=False)
    gdpr_email = models.BooleanField(default=False)
    gdpr_phone = models.BooleanField(default=False)

    def __str__(self):
        return str(self.subscription)


class Donation(models.Model):
    donator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donaton',
                              verbose_name="Donator")
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, related_name='dmembership_package', verbose_name="Membership Package")
    amount = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    email_address = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    stripe_id = models.CharField(max_length=255, blank=True)
    stripe_payment_id = models.CharField(max_length=255, blank=True)
    validated = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
