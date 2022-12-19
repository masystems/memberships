from django.contrib import admin
from .models import MembershipPackage, Price, PaymentMethod, Member, MembershipSubscription, Payment, Equine, Donation


class MembershipPackagesAdmin(admin.ModelAdmin):
    list_display = ('organisation_name', 'owner', 'cloud_lines_domain', 'stripe_acct_id', 'created')
    list_filter = ('organisation_name', 'owner', 'cloud_lines_domain', 'stripe_acct_id', 'created')
    search_fields = ['organisation_name', 'owner', 'cloud_lines_domain', 'stripe_acct_id', 'active', 'created']
    ordering = ['organisation_name']
    empty_value_display = '-empty-'

    save_on_top = True


admin.site.register(MembershipPackage, MembershipPackagesAdmin)


class MembershipSubInline(admin.StackedInline):
    model = MembershipSubscription


class MembersAdmin(admin.ModelAdmin):
    # list_display = ('user_account', 'email', 'first_name', 'last_name')
    # list_filter = ('user_account', 'email', 'first_name', 'last_name')
    # search_fields = ['user_account', 'email', 'first_name', 'last_name']
    # ordering = ['last_name', ]
    # empty_value_display = '-empty-'

    save_on_top = True
    inlines = [MembershipSubInline]


admin.site.register(Member, MembersAdmin)


class EquestrianAdmin(admin.ModelAdmin):
    list_filter = ('membership_package',)
    search_fields = ['membership_package']
    ordering = ['membership_package']
    empty_value_display = '-empty-'

    save_on_top = True


admin.site.register(Equine, EquestrianAdmin)

class MembersSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('membership_number', 'member', 'membership_package', 'payment_method', 'price', 'validated', 'membership_start', 'membership_expiry', 'active')
    list_filter = ('membership_package', 'payment_method', 'price', 'validated', 'membership_start', 'membership_expiry', 'active')
    search_fields = ['membership_number', 'member__user_account__first_name', 'member__user_account__last_name', 'member__user_account__email']
    ordering = ['membership_number', ]
    empty_value_display = ''
    save_on_top = True

admin.site.register(MembershipSubscription, MembersSubscriptionAdmin)
admin.site.register(Donation)
admin.site.register(Price)
admin.site.register(PaymentMethod)
admin.site.register(Payment)
