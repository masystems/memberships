from django.contrib import admin
from .models import MembershipPackage, Member, Equine


class MembershipPackagesAdmin(admin.ModelAdmin):
    list_display = ('organisation_name', 'owner', 'cloud_lines_account', 'stripe_id', 'created')
    list_filter = ('organisation_name', 'owner', 'cloud_lines_account', 'stripe_id', 'created')
    search_fields = ['organisation_name', 'owner', 'cloud_lines_account', 'stripe_id', 'active', 'created']
    ordering = ['organisation_name']
    empty_value_display = '-empty-'

    save_on_top = True


admin.site.register(MembershipPackage, MembershipPackagesAdmin)


class MembersAdmin(admin.ModelAdmin):
    list_display = ('membership_number', 'user_account', 'membership_package')
    list_filter = ('membership_number', 'user_account', 'membership_package')
    search_fields = ['membership_number', 'user_account']
    ordering = ['membership_number', ]
    empty_value_display = '-empty-'

    save_on_top = True


admin.site.register(Member, MembersAdmin)


class EquestrianAdmin(admin.ModelAdmin):
    list_filter = ('membership_package',)
    search_fields = ['membership_package']
    ordering = ['membership_package']
    empty_value_display = '-empty-'

    save_on_top = True


admin.site.register(Equine, EquestrianAdmin)