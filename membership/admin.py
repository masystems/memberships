from django.contrib import admin
from .models import MembershipPackage, Member, MembershipSubscription, Equine


class MembershipPackagesAdmin(admin.ModelAdmin):
    list_display = ('organisation_name', 'owner', 'cloud_lines_account', 'stripe_acct_id', 'created')
    list_filter = ('organisation_name', 'owner', 'cloud_lines_account', 'stripe_acct_id', 'created')
    search_fields = ['organisation_name', 'owner', 'cloud_lines_account', 'stripe_acct_id', 'active', 'created']
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
admin.site.register(MembershipSubscription)

class EquestrianAdmin(admin.ModelAdmin):
    list_filter = ('membership_package',)
    search_fields = ['membership_package']
    ordering = ['membership_package']
    empty_value_display = '-empty-'

    save_on_top = True


admin.site.register(Equine, EquestrianAdmin)