from django.contrib import admin

# Register your models here.
from Attendance.models import EmployeeInfo, OriginalCard, ShiftsInfo, EmployeeSchedulingInfo, EditAttendanceType, \
    EditAttendance, LeaveType, LeaveInfo, AttendanceExceptionStatus, AttendanceInfo, EmployeeInfoImport, \
    OriginalCardImport
from Attendance.views import loading_data, get_path


@admin.register(EmployeeInfo)
class EmployeeInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'level', 'emp_status')
    list_filter = ('level', 'emp_status', )
    search_fields = ('name', 'code', )
    pass

@admin.register(EmployeeInfoImport)
class EmployeeInfoImportAdmin(admin.ModelAdmin):
    actions = ['upload_loading', ]

    def upload_loading(self, request, queryset):
        path = get_path(queryset)
        loading_data(path, EmployeeInfo)

    upload_loading.short_description = '解析文件'
    pass

@admin.register(OriginalCard)
class OriginalCardAdmin(admin.ModelAdmin):
    model = OriginalCard
    list_display = ('emp', 'attendance_card', )
    # list_filter = ('level', 'emp_status', )
    search_fields = ('emp__code', 'emp__name', )
    date_hierarchy = 'attendance_card'


    pass

@admin.register(OriginalCardImport)
class OriginalCardImportAdmin(admin.ModelAdmin):
    actions = ['upload_loading', ]

    def upload_loading(self, request, queryset):
        path = get_path(queryset)
        loading_data(path, OriginalCard)

    upload_loading.short_description = '解析文件'
    pass

@admin.register(ShiftsInfo)
class ShiftsInfoAdmin(admin.ModelAdmin):
    pass

@admin.register(EmployeeSchedulingInfo)
class EmployeeSchedulingInfoAdmin(admin.ModelAdmin):
    pass
@admin.register(EditAttendanceType)
class EditAttendanceTypeAdmin(admin.ModelAdmin):
    pass

@admin.register(EditAttendance)
class EditAttendanceAdmin(admin.ModelAdmin):
    pass

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    pass

@admin.register(LeaveInfo)
class LeaveInfoAdmin(admin.ModelAdmin):
    pass

@admin.register(AttendanceExceptionStatus)
class AttendanceExceptionStatusAdmin(admin.ModelAdmin):
    pass

@admin.register(AttendanceInfo)
class AttendanceInfoAdmin(admin.ModelAdmin):
    pass

# admin.site.register(EmployeeInfo, EmployeeInfoAdmin)
# admin.site.register(OriginalCard, OriginalCardAdmin)
# admin.site.register(ShiftsInfo, ShiftsInfoAdmin)
# admin.site.register(EmployeeSchedulingInfo, EmployeeSchedulingInfoAdmin)
# admin.site.register(EditAttendanceType, EditAttendanceTypeAdmin)
# admin.site.register(EditAttendance, EditAttendanceAdmin)
# admin.site.register(LeaveType, LeaveTypeAdmin)
# admin.site.register(LeaveInfo, LeaveInfoAdmin)
# admin.site.register(AttendanceExceptionStatus, AttendanceExceptionStatusAdmin)
# admin.site.register(AttendanceInfo, AttendanceInfoAdmin)
# 设置站点标题
admin.site.site_header = '考勤信息处理平台'
admin.site.site_title = '考勤信息处理'