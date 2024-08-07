from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


class MembershipPackage(models.Model):
    organisation_name = models.CharField(max_length=50)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='owner', verbose_name="Owner")
    admins = models.ManyToManyField(User, blank=True, related_name='admins', verbose_name="Admins")
    stripe_acct_id = models.CharField(max_length=255, blank=True)
    stripe_owner_id = models.CharField(max_length=255, blank=True)
    stripe_product_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    BOLTONS = (
        ('none', 'None'),
        ('equine', 'Equine'),
    )
    bolton = models.CharField(max_length=12, choices=BOLTONS, null=True, default='none',
                              help_text="Boltons add additional fields to your member form.")
    BUSINESS_TYPE = (
        ('individual', 'Individual'),
        ('company', 'Company '),
        ('non_profit', 'Non Profit '),
    )
    business_type = models.CharField(max_length=19, choices=BUSINESS_TYPE, default='individual',
                                help_text="Select your business type")
    INCREMENTS = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )
    payment_increments = models.CharField(max_length=12, choices=INCREMENTS, null=True, default='monthly',
                              help_text="In what increments your payments are made")
    
    custom_fields = models.TextField(blank=True)
    cloud_lines_domain = models.CharField(max_length=100, blank=True, default='cloud-lines.com',
                                           help_text="Link your membership account to your cloud-lines account")
    cloud_lines_token = models.CharField(max_length=255, blank=True)

    enabled = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    payment_reminder_email = models.TextField(blank=True)

    def __str__(self):
        return self.organisation_name


class Price(models.Model):
    """
    Membership Types,
    Payment Types
    """
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, related_name='pmembership_package', verbose_name="Membership Package")
    stripe_price_id = models.CharField(max_length=255, blank=True)
    nickname = models.CharField(max_length=255, blank=True)
    INTERVAL = (
        ('month', 'Monthly'),
        ('year', 'Yearly '),
        ('one_time', 'One Time'),
    )
    interval = models.CharField(max_length=19, choices=INTERVAL, null=True, default='monthly',
                                      help_text="Payment frequency")
    currency = models.CharField(max_length=255, default="GBP", blank=True)
    amount = models.CharField(max_length=255, blank=True)
    visible = models.BooleanField(default=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.membership_package.organisation_name} - {self.nickname}"


class PaymentMethod(models.Model):
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, related_name='pmmembership_package', verbose_name="Membership Package")
    payment_name = models.CharField(max_length=250)
    information = models.TextField(blank=True)
    visible = models.BooleanField(default=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.membership_package.organisation_name} - {self.payment_name}"


class Member(models.Model):
    user_account = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    company = models.CharField(max_length=255, blank=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=255, blank=True)
    county = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=255, blank=True, null=True)
    secondary_contact_number = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user_account.email} - {self.user_account.username}"


class MembershipSubscription(models.Model):
    membership_number = models.IntegerField(blank=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='subscription', verbose_name="Membership Subscription")
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, related_name='membership_package', verbose_name="Membership Package")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE, blank=True, null=True, related_name='spayment_method', verbose_name="Payment Method")
    price = models.ForeignKey(Price, on_delete=models.CASCADE, blank=True, null=True, related_name='price', verbose_name="Price")
    stripe_payment_token = models.CharField(max_length=255, blank=True)
    stripe_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    stripe_schedule_id = models.CharField(max_length=255, blank=True)
    validated = models.BooleanField(default=False)
    comments = models.TextField(blank=True)
    membership_start = models.DateField(null=True, blank=True, default=datetime.now)
    membership_expiry = models.DateField(null=True, blank=True)
    gift_aid = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)
    custom_fields = models.TextField(blank=True)
    last_reminder = models.DateField(null=True, blank=True)
    remaining_amount = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.membership_package.organisation_name


class Payment(models.Model):
    subscription = models.ForeignKey(MembershipSubscription, on_delete=models.CASCADE, related_name='payment', verbose_name="Subscription Payment")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, related_name='payment_method', verbose_name="Payment Method")
    payment_number = models.CharField(max_length=255, unique=True)
    TYPE = (
        ('subscription', 'Subscription'),
        ('donation', 'Donation'),
        ('merchandise', 'Merchandise'),
        ('fees', 'Fees'),
        ('adverts', 'Adverts'),
        ('one off', 'One Off'),
    )
    type = models.CharField(max_length=25, choices=TYPE, null=True, default='subscription', verbose_name="Payment Type")
    amount = models.CharField(max_length=255, blank=True)
    comments = models.TextField(null=True, blank=True)
    created = models.DateField(default=datetime.now)
    gift_aid = models.BooleanField(default=False)
    gift_aid_percentage = models.CharField(max_length=255, blank=True)
    stripe_id = models.CharField(max_length=255, blank=True)


class Equine(models.Model):
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, blank=True, null=True, related_name='emembership_package', verbose_name="Equine Membership Package")
    subscription = models.ForeignKey(MembershipSubscription, on_delete=models.CASCADE, blank=True, null=True, related_name='esub', verbose_name="Equine Subscription")
    date_resigned = models.DateField(blank=True, null=True)
    date_entered = models.DateField(blank=True, null=True)
    date_updated = models.DateField(blank=True, null=True)
    actual_renewal = models.DateField(blank=True, null=True)
    fk_renewal_status = models.CharField(max_length=250, blank=True)
    mail_tag = models.BooleanField(default=False)
    anonymous = models.BooleanField(default=False)
    do_not_mail = models.BooleanField(default=False)
    do_not_mail_date = models.DateField(blank=True, null=True)
    do_not_mail_reason = models.CharField(max_length=250, blank=True)
    area_code = models.CharField(max_length=250, blank=True)
    overseas = models.BooleanField(default=False)
    home_telephone = models.CharField(max_length=250, blank=True)
    office_telephone = models.CharField(max_length=250, blank=True)
    source = models.CharField(max_length=250, blank=True)
    donor = models.BooleanField(default=False)
    signature_given_date = models.DateField(blank=True, null=True)
    owner_breeder = models.BooleanField(default=False)
    volunteer = models.BooleanField(default=False)
    no_raffle_tickets = models.BooleanField(default=False)
    so_started = models.DateField(blank=True, null=True)
    so_amount = models.CharField(max_length=250, blank=True)
    bad_address = models.BooleanField(default=False)
    second_name = models.CharField(max_length=250, blank=True)
    returned_gdpr_date = models.DateField(blank=True, null=True)
    gift_aid_decision = models.BooleanField(default=False)
    gift_aid_type = models.CharField(max_length=250, blank=True)
    gift_aid_decision_made_on = models.DateField(blank=True, null=True)
    gift_aid_signature = models.CharField(max_length=250, blank=True)
    contact_via_email = models.BooleanField(default=False)
    contact_via_email_date = models.DateField(blank=True, null=True)
    gdpr_post = models.BooleanField(default=False)
    gdpr_email = models.BooleanField(default=False)
    gdpr_phone = models.BooleanField(default=False)

    def __str__(self):
        return str(self.subscription)

    def attrs(self):
        for attr, value in self.__dict__.items():
            yield attr, value


class Donation(models.Model):
    donator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donaton',
                              verbose_name="Donator", blank=True, null=True)
    membership_package = models.ForeignKey(MembershipPackage, on_delete=models.CASCADE, related_name='dmembership_package', verbose_name="Membership Package")
    amount = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    email_address = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    stripe_id = models.CharField(max_length=255, blank=True)
    stripe_payment_id = models.CharField(max_length=255, blank=True)
    validated = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    gift_aid = models.BooleanField(default=False)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=255, blank=True)
    county = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=255, blank=True)
