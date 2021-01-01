from django.db import models
from django.contrib.auth.models import User


class Donation(models.Model):
    donator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Donator',
                              verbose_name="Donator")
    organisation_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=255)
    email_address = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    stripe_id = models.CharField(max_length=255, blank=True)
    validated = models.BooleanField(default=False)


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

    membership_price_per_month = models.DecimalField(blank=False,
                                                     max_digits=5,
                                                     decimal_places=2,
                                                     help_text="Price in £ per month",
                                                     verbose_name="Membership Price Per Month")
    membership_price_per_month_id = models.CharField(max_length=255, blank=True)
    membership_price_per_year = models.DecimalField(blank=False,
                                                    max_digits=5,
                                                    decimal_places=2,
                                                    help_text="Price in £ per year",
                                                    verbose_name="Membership Price Per Year")
    membership_price_per_year_id = models.CharField(max_length=255, blank=True)

    cloud_lines_account = models.CharField(max_length=100, blank=True,
                                           help_text="Link your membership account to your cloud-lines account")
    enabled = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.organisation_name


class Member(models.Model):
    user_account = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    # email = models.EmailField(max_length=255)
    # first_name = models.CharField(max_length=255)
    # last_name = models.CharField(max_length=255)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=255, blank=True)
    county = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user_account.email


class MembershipSubscription(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True, related_name='subscription', verbose_name="Membership Subscription")
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, blank=True, null=True, related_name='membership_package', verbose_name="Membership Package")
    stripe_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    validated = models.BooleanField(default=False)

    RECORD_TYPE = (
        ('member', 'Member'),
        ('complimentry', 'Complimentry'),
        ('donor', 'Donor')
    )
    record_type = models.CharField(max_length=12, choices=RECORD_TYPE, null=True, default='member',
                                   help_text="Type of member")

    membership_number = models.CharField(max_length=100, unique=True)

    CATEGORY = (
        ('member', 'Member'),
        ('joint_members', 'Joint Members'),
        ('friend', 'Friend'),
        ('joint_friend', 'Joint Friend'),
        ('corporate', 'Corporate'),
        ('life_member', 'Life Member'),
        ('overseas_supplement', 'Overseas Supplement'),
        ('junior', 'Junior'),
        ('teen', 'Teen'),
        ('governor', 'Governor')
    )
    category = models.CharField(max_length=19, choices=CATEGORY, null=True, default='member',
                                help_text="Category of member")

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

    BILLING_PERIOD = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly '),
    )
    billing_period = models.CharField(max_length=19, choices=BILLING_PERIOD, null=True, default='monthly',
                                      help_text="Payment frequency")

    # membership_price = models.DecimalField(blank=False, max_digits=5, decimal_places=2, help_text="Price in £ for requency given")

    comments = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.membership_number


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
        return str(self.member) if self.member else ''