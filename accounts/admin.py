from django.contrib import admin
from .models import User, Student, Company, Admin as AdminProfile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'role', 'is_staff')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('firstName', 'lastName', 'department', 'univWillaya')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('companyName', 'location', 'isApproved', 'isBlacklisted')
    readonly_fields = ('registreCommerce',)

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('firstName', 'lastName', 'department', 'university')