import xadmin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from xadmin import site
from xadmin.plugins.actions import BaseActionView
from xadmin.views import CommAdminView, filter_hook

from Attendance.models import EmployeeInfo, OriginalCard, ShiftsInfo, EmployeeSchedulingInfo, EditAttendanceType, \
    EditAttendance, LeaveType, LeaveInfo, AttendanceExceptionStatus, AttendanceInfo, EmployeeInfoImport, \
    OriginalCardImport, LegalHoliday
from Attendance.views import get_path, loading_data, data_select, ShareContext, shift_swap_select, \
    cal_attendance_select, edit_attendance_cal


class SelectedShiftsInfoAction(BaseActionView):

    # 这里需要填写三个属性
    #: 相当于这个 Action 的唯一标示, 尽量用比较针对性的名字
    action_name = "排班选择"
    #: 描述, 出现在 Action 菜单中, 可以使用 ``%(verbose_name_plural)s`` 代替 Model 的名字.
    description = ('排班选择 %(verbose_name_plural)s')
    model_perm = 'change'    #: 该 Action 所需权限


    # 而后实现 do_action 方法
    # @filter_hook
    def do_action(self, queryset):
        # queryset 是包含了已经选择的数据的 queryset
        context = self.get_context()
        # 不需要更新
        # context.update({"form": ShiftsInfoDateForm(),
        #                 "title": "考勤计算",})
        # print(type(ShiftsInfoForm()))
        # print(ShiftsInfoForm().__dict__)
        self.message_user("选择计算的开始日期和结束日期,以及班次(确保已完成法定节假日处理)")
        # print(context)
        # return render(self.request, 'Attendance/selected.html',
        #                   context=context)
        # print(self.request.__dict__)
        print(self.request.path)
        # print(self.message_user)
        ShareContext(context=context, path=self.request.path, query_list=queryset)
        # return HttpResponse(data_select)
        return redirect(data_select)
        # return get_scheduling_info(request=self.request, message_user=self.message_user, context=context, )

class ShiftSelectAction(BaseActionView):

    # 这里需要填写三个属性
    #: 相当于这个 Action 的唯一标示, 尽量用比较针对性的名字
    action_name = "调班"
    #: 描述, 出现在 Action 菜单中, 可以使用 ``%(verbose_name_plural)s`` 代替 Model 的名字.
    description = ('调班 %(verbose_name_plural)s')
    model_perm = 'change'    #: 该 Action 所需权限

    # 而后实现 do_action 方法
    def do_action(self, queryset):
        # queryset 是包含了已经选择的数据的 queryset
        # for obj in queryset:
        #     # obj 的操作
        #     pass
        # # 返回 HttpResponse
        context = self.get_context()
        # context.update({"form": ShiftsInfoForm(),
        #                 "title": "选择班次",})
        # print(type(ShiftsInfoForm()))
        # print(ShiftsInfoForm().__dict__)
        self.message_user("选择要交换的日期")
        ShareContext(context=context, path=self.request.path, query_list=queryset)
        # print(context)
        return redirect(shift_swap_select)

class CalAttendanceAction(BaseActionView):

    # 这里需要填写三个属性
    #: 相当于这个 Action 的唯一标示, 尽量用比较针对性的名字
    action_name = "考勤计算"
    #: 描述, 出现在 Action 菜单中, 可以使用 ``%(verbose_name_plural)s`` 代替 Model 的名字.
    description = ('考勤计算 %(verbose_name_plural)s')
    model_perm = 'change'    #: 该 Action 所需权限

    # 而后实现 do_action 方法
    def do_action(self, queryset):
        # queryset 是包含了已经选择的数据的 queryset
        # for obj in queryset:
        #     # obj 的操作
        #     pass
        # # 返回 HttpResponse
        context = self.get_context()
        # context.update({"form": ShiftsInfoForm(),
        #                 "title": "选择班次",})
        # print(type(ShiftsInfoForm()))
        # print(ShiftsInfoForm().__dict__)
        self.message_user("选择要计算考勤的日期")
        ShareContext(context=context, path=self.request.path, query_list=queryset)
        # print(context)
        return redirect(cal_attendance_select)


@xadmin.sites.register(EmployeeInfo)
class EmployeeInfoAdmin(object):
    list_display = ('code', 'name', 'level', 'emp_status')
    list_filter = ('level', 'emp_status', )
    search_fields = ('name', 'code', )
    actions = [SelectedShiftsInfoAction, ShiftSelectAction, CalAttendanceAction, 'test']

    def test(self, request, queryset):
        return redirect(data_select)
        #
        # 最终通过这个函数进行考勤计算
        # cal_scheduling_info(request, queryset, date_range, shift_name, )

        pass

    test.short_description = '测试'

    pass


@xadmin.sites.register(EmployeeInfoImport)
class EmployeeInfoImportAdmin(object):
    actions = ['upload_loading',]

    def upload_loading(self, request, queryset):
        path = get_path(queryset)
        name_list = loading_data(path, EmployeeInfo)
        if len(name_list):
            self.message_user("{num}没有导入成功,{name}".format(
                num=len(name_list),
                name='、'.join(sorted(set(name_list), key=name_list.index))))
    upload_loading.short_description = '解析文件'
    pass

@xadmin.sites.register(OriginalCard)
class OriginalCardAdmin(object):
    model = OriginalCard
    list_display = ('emp', 'attendance_card', )
    # list_filter = ('level', 'emp_status', )
    search_fields = ('emp__code', 'emp__name', )
    date_hierarchy = 'attendance_card'


    pass

@xadmin.sites.register(OriginalCardImport)
class OriginalCardImportAdmin(object):
    actions = ['upload_loading', ]

    def upload_loading(self, request, queryset):
        path = get_path(queryset)
        name_list = loading_data(path, OriginalCard)
        if len(name_list):
            self.message_user("{num}没有导入成功,{name}".format(
                num=len(name_list),
                name='、'.join(sorted(set(name_list), key=name_list.index))))

    upload_loading.short_description = '解析文件'
    pass

@xadmin.sites.register(ShiftsInfo)
class ShiftsInfoAdmin(object):
    list_display = ('name', 'type_shift', 'check_in', 'check_in_end', 'check_out_start', 'check_out', 'late_time',
                    'leave_early_time', 'absenteeism_time', 'status')
    pass

@xadmin.sites.register(LegalHoliday)
class LegalHolidayAdmin(object):
    list_display = ('legal_holiday_name', 'legal_holiday', 'status')
    list_filter = ('status',)
    ordering = ('legal_holiday',)
    pass

@xadmin.sites.register(EmployeeSchedulingInfo)
class EmployeeSchedulingInfoAdmin(object):
    # actions = [SelectedShiftsInfoAction, ShiftSelectAction, ]
    list_display = ('emp', 'attendance_date', 'shifts_verbose_name')
    list_filter = ('attendance_date',)
    search_fields = ('emp__code', 'emp__name')
    ordering = ('emp', 'attendance_date')
    pass

@xadmin.sites.register(EditAttendanceType)
class EditAttendanceTypeAdmin(object):
    pass

@xadmin.sites.register(EditAttendance)
class EditAttendanceAdmin(object):
    actions = ['edit_attendance']
    list_display = ('emp', 'edit_attendance_date', 'edit_attendance_time_start', 'edit_attendance_time_end',
                    'edit_attendance_type', )
    list_filter = ('edit_attendance_type', 'edit_attendance_date')
    search_fields = ('emp__code', 'emp__name')

    def edit_attendance(self, request, queryset):
        edit_attendance_cal(queryset)
        pass
    pass

@xadmin.sites.register(LeaveType)
class LeaveTypeAdmin(object):
    pass

@xadmin.sites.register(LeaveInfo)
class LeaveInfoAdmin(object):
    pass

@xadmin.sites.register(AttendanceExceptionStatus)
class AttendanceExceptionStatusAdmin(object):
    pass

@xadmin.sites.register(AttendanceInfo)
class AttendanceInfoAdmin(object):
    list_display = ('emp', 'attendance_date', 'check_in', 'check_in_status', 'check_out', 'check_out_status', 'check_status')
    list_filter = ('attendance_date', 'check_in_status', 'check_out_status', 'check_status', 'emp__level', 'emp__emp_status')
    search_fields = ('emp__code', 'emp__name')
    ordering = ('emp', 'attendance_date')

    def status(self):

        pass
    pass

class GlobalSetting(object):
    # 设置base_site.html的Title
    site_title = '考勤信息处理'
    # 设置base_site.html的Footer
    site_footer  = '考勤信息处理平台'
xadmin.site.register(CommAdminView, GlobalSetting)

# xadmin.site.register(EmployeeInfo)
# xadmin.site.register(OriginalCard)
# xadmin.site.register(ShiftsInfo)
# xadmin.site.register(EmployeeSchedulingInfo)
# xadmin.site.register(EditAttendanceType)
# xadmin.site.register(EditAttendance)
# xadmin.site.register(LeaveType)
# xadmin.site.register(LeaveInfo)
# xadmin.site.register(AttendanceExceptionStatus)
# xadmin.site.register(AttendanceInfo)

