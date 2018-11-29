import calendar
import datetime

import xlrd
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
# Create your views here.
from django.urls import reverse

from Attendance.forms import UserForm, ChangePwdForm
from Attendance.models import OriginalCardImport, EmployeeInfo, EmployeeSchedulingInfo, ShiftsInfo, LegalHoliday, \
    AttendanceInfo, OriginalCard, AttendanceExceptionStatus, EditAttendance, LeaveInfo, LeaveDetail, AttendanceTotal, \
    Limit, LeaveType, LimitStatus, HelpContext


# TODO 返回友好型页面，而不是报错
class ShareContext:
    """
    共享 xadmin 数据 ，跳转到个人绘制的 视图 时，仍套用xadmin的框架
    """

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ShareContext, cls).__new__(cls)
        return cls.instance

    def __init__(self, context=None, path=None, query_list=None, form=None, title=None, templates=None, callback=None,
                 argument_dict=None):
        if context is not None:
            self.share_context = context
        if path is not None:
            self.path = path
        if query_list is not None:
            self.query_list = query_list
        if form is not None:
            self.form = form
        if title is not None:
            self.title = title
        if templates is not None:
            self.templates = templates
        if callback is not None:
            self.callback = callback
        if argument_dict is not None:
            assert isinstance(argument_dict, dict), "使用错误，应为字典"
            self.argument_dict = argument_dict

    @staticmethod
    def clear_data():
        """
        清除所有私有数据
        :return:
        """
        for key in ShareContext().__dict__:
            setattr(ShareContext(), key, None)
        pass


def get_path(queryset):
    """
    获取上传文件的路劲
    :param queryset:
    :return:
    """
    #  数据导入，待清理
    tables = [OriginalCardImport]
    # 如果选择2个则报错
    # print(len(queryset))
    assert len(queryset) == 1, "只能选择一条记录"
    for one in queryset:
        print(type(one))
        print(one.path_name)
        for table in tables:
            if isinstance(one, table):
                return str(one.path_name)
    raise UserWarning("无法获取上传的路径", queryset)
    pass


def original_card_import(path):
    name_err_list = []
    original_ins_list = []
    cols_dict = {'emp': '工号', 'attendance_card': '出勤时间'}
    # excel 对应字段索引
    table_col_index = {}
    # 数据结构为 工号：出勤日期
    original_card_dict = {}
    # 获取原始打卡excel表实例
    workbook = xlrd.open_workbook(path)
    # 获取 excel表第一个sheet
    wb_instance = workbook.sheet_by_index(0)
    # 获取所有的标题
    col_title = [wb_instance.cell_value(0, col) for col in range(wb_instance.ncols)]
    # 判断列标题没有重复值 （数组去除重复值后，比较数组长度）
    assert len(sorted(set(col_title), key=col_title.index)) == len(col_title)
    # 判断是否存在于字典,存在
    for key, verbose_name in cols_dict.items():
        try:
            table_col_index[key] = col_title.index(verbose_name)
        except ValueError:
            # UserWarning as err
            # err.args[0] 获取错误的参数
            raise UserWarning("列标题不存在", verbose_name)
    # 读取每一行数据，并将其值赋值给 对象
    for row in range(1, wb_instance.nrows):
        # 获取工号
        emp_code = wb_instance.cell_value(row, table_col_index['emp'])
        # 获取 出勤日期
        emp_attendance_datetime = wb_instance.cell_value(row, table_col_index['attendance_card'])
        if original_card_dict.get(emp_code) is None:
            original_card_dict[emp_code] = []
        original_card_dict[emp_code].append(datetime.datetime.strptime(emp_attendance_datetime, "%Y-%m-%d %H:%M:%S"))
    for code, attendance_datetime in original_card_dict.items():
        try:
            emp = EmployeeInfo.objects.filter(code=code).get()
        # 不存在或者不止一个
        except EmployeeInfo.DoesNotExist:
            #  没有此用户，跳过
            name_err_list.append(code)
            continue
            pass
        # 导入考勤的最小时间、最大时间
        start_time = sorted(attendance_datetime)[0]
        end_time = sorted(attendance_datetime)[-1]
        # 获取数据库数据
        original_card_list = get_original_card_list_import(emp, start_time, end_time)
        # 不重复的记录
        differ_original = set(attendance_datetime) - set(original_card_list)
        for one in differ_original:
            original_ins_list.append(OriginalCard(emp=emp, attendance_card=one))
    OriginalCard.objects.bulk_create(original_ins_list)
    return name_err_list


def get_original_card_list_import(emp, start_time, end_time):
    # 获取
    query_list = Q(emp=emp) & Q(attendance_card__gte=start_time) & Q(attendance_card__lte=end_time)
    return OriginalCard.objects.filter(query_list).values_list('attendance_card', flat=True)


def date_range(start_date, end_date):
    """
    生成一个 起始时间 到 结束时间 的一个列表
    TODO 起始时间和结束时间相差过大时，考虑使用 yield
    :param start_date:
    :param end_date:
    :return:
    """
    date_tmp = [start_date, ]
    # print(date_tmp[-1])
    assert date_tmp[-1] <= end_date, "开始日期大于结束日期"
    while date_tmp[-1] < end_date:
        date_tmp.append(date_tmp[-1] + datetime.timedelta(days=1))
    return date_tmp
    pass


# 排班计算
def cal_scheduling_info(queryset, start_date, end_date, shifts_name, ):
    """
    将 周一 到 周五 排 shifts_name 的班次，其余的排 节假日班次；
    节假日班次需要自己创建
    :param queryset: 人员列表
    :param start_date:
    :param end_date:
    :param shifts_name: 班次
    :return:
    """
    emp_scheduling_info_list = []
    legal_holiday_dict = {}
    # Q & = and ， | = or
    question = Q(status='1') & Q(legal_holiday__gte=start_date) & Q(legal_holiday__lte=end_date)
    #  拆包
    legal_holiday_dict_list = LegalHoliday.objects.filter(question).values('legal_holiday', 'legal_holiday_name')
    for legal_holiday_dict_one in legal_holiday_dict_list:
        legal_holiday_dict[legal_holiday_dict_one['legal_holiday']] = legal_holiday_dict_one['legal_holiday_name']
    print(legal_holiday_dict)
    for one in queryset:
        # 删除之前的排班
        delete_question = Q(emp=one) & Q(attendance_date__gte=start_date) & Q(attendance_date__lte=end_date)
        EmployeeSchedulingInfo.objects.filter(delete_question).delete()
        for date in date_range(start_date, end_date):
            emp_scheduling_info = EmployeeSchedulingInfo()
            emp_scheduling_info.emp = EmployeeInfo.objects.get(id=one.id)
            emp_scheduling_info.attendance_date = date
            # 班次选择
            # print(date)
            if date in legal_holiday_dict.keys():
                emp_scheduling_info.shifts_name = ShiftsInfo.objects.get(name='节假日班次')
                emp_scheduling_info.shifts_verbose_name = legal_holiday_dict[date]
            elif datetime.date.isoweekday(date) in (6, 7):
                emp_scheduling_info.shifts_name = ShiftsInfo.objects.get(name='节假日班次')
                emp_scheduling_info.shifts_verbose_name = emp_scheduling_info.shifts_name
            else:
                emp_scheduling_info.shifts_name = ShiftsInfo.objects.get(id=shifts_name)
                emp_scheduling_info.shifts_verbose_name = emp_scheduling_info.shifts_name
            emp_scheduling_info.operate = datetime.datetime.now()
            emp_scheduling_info_list.append(emp_scheduling_info)
            pass
        pass
    EmployeeSchedulingInfo.objects.bulk_create(emp_scheduling_info_list)

    pass


# 排班交换
def shift_swap(queryset, start_date, end_date, ):
    """
    交换排班
    TODO 待优化
    :param queryset: 人员列表
    :param start_date:
    :param end_date:
    :return:
    """
    for one in queryset:
        query = Q(emp=one.code)
        swap_before = EmployeeSchedulingInfo.objects.filter(query & Q(attendance_date=start_date)).get()
        swap_after = EmployeeSchedulingInfo.objects.filter(query & Q(attendance_date=end_date)).get()
        swap_before.shifts_name, swap_after.shifts_name = swap_after.shifts_name, swap_before.shifts_name
        swap_before.shifts_verbose_name, swap_after.shifts_verbose_name = swap_after.shifts_verbose_name, swap_before.shifts_verbose_name
        swap_before.operate = datetime.datetime.now()
        swap_after.operate = datetime.datetime.now()
        swap_before.save()
        swap_after.save()
    pass


# 假期拆分
def leave_split(leave_info_ins):
    assert isinstance(leave_info_ins, LeaveInfo), "leave_info_ins 不是 LeaveInfo 对象"
    leave_detail_ins_list = []
    shift_info_dict = get_shift_info_dict()
    # TODO 没有排班会影响<假期拆分>的结果
    scheduling_info_dict = get_scheduling_info_dict(leave_info_ins.emp, leave_info_ins.start_date,
                                                    leave_info_ins.end_date)
    # question = Q(emp=leave_info_ins.emp) & Q(leave_date__gte=leave_info_ins.start_date) & Q(
    #     leave_date__lte=leave_info_ins.end_date)
    # models 中进行了关联，直接通过实例就可以了
    # 无 ID 不会删除已关联的 LeaveDetail
    question = Q(leave_info_id=leave_info_ins)
    LeaveDetail.objects.filter(question).delete()
    for attendance_date, shift_name in scheduling_info_dict.items():
        # 假期类型不含节假日
        if leave_info_ins.leave_type.legal_include is False:
            # 班次为节假日，跳过
            if shift_info_dict[shift_name].type_shift is False:
                continue
        leave_detail_ins = LeaveDetail()
        leave_detail_ins.emp = leave_info_ins.emp
        leave_detail_ins.leave_info_id = leave_info_ins
        leave_detail_ins.leave_date = attendance_date
        # 当前日期不是第一天 或最后一天 ，开始日期和结束日期为 班次的 上午上班时间、 下午下班时间
        leave_detail_ins.leave_detail_time_start = shift_info_dict[shift_name].check_in
        leave_detail_ins.leave_detail_time_end = shift_info_dict[shift_name].check_out
        # 当前日期为开始日期
        if attendance_date == leave_info_ins.start_date:
            # 开始时间小于 check_in_end 则 开始请假时间 为早上
            if leave_info_ins.leave_info_time_start <= shift_info_dict[shift_name].check_in_end:
                leave_detail_ins.leave_detail_time_start = leave_info_ins.leave_info_time_start
            # 开始时间大于 check_out_start 则 开始请假时间 为下午
            elif leave_info_ins.leave_info_time_start >= shift_info_dict[shift_name].check_out_start:
                leave_detail_ins.leave_detail_time_start = None
            # 否则报错
            else:
                raise UserWarning("假期起始时间不正确")
        # 当前日期为结束日期
        if attendance_date == leave_info_ins.end_date:
            # leave_info_time_end 小于 check_in_end 则 结束请假时间为早上
            if leave_info_ins.leave_info_time_end <= shift_info_dict[shift_name].check_in_end:
                leave_detail_ins.leave_detail_time_end = None
            # leave_info_time_end 大于 check_out_start 则 结束请假时间为下午
            elif leave_info_ins.leave_info_time_end >= shift_info_dict[shift_name].check_out_start:
                leave_detail_ins.leave_detail_time_end = leave_info_ins.leave_info_time_end
            else:
                raise UserWarning("假期结束时间不正确")
        leave_detail_ins.leave_type = leave_info_ins.leave_type
        leave_detail_ins.leave_info_status = leave_info_ins.leave_info_status
        #  判断是否有重复单据
        leave_info_distinct(leave_detail_ins)
        leave_detail_ins.count_length = float((0 if leave_detail_ins.leave_detail_time_start is None else 0.5) + (
            0 if leave_detail_ins.leave_detail_time_end is None else 0.5))
        leave_detail_ins_list.append(leave_detail_ins)
    return leave_detail_ins_list


def leave_info_distinct(leave_detail_ins_tmp):
    assert isinstance(leave_detail_ins_tmp, LeaveDetail), "使用错误，不是请假明细实例"
    query_list = Q(emp=leave_detail_ins_tmp.emp) & Q(leave_date=leave_detail_ins_tmp.leave_date) & Q(
        leave_info_status=leave_detail_ins_tmp.leave_info_status)
    # 上午/下午  全天  上午  下午 无 ,共5种情况 不需要初始化 attendance_date
    leave_detail_ins_list = LeaveDetail.objects.filter(query_list)
    attendance_date = {}
    for one in leave_detail_ins_list:
        if one.leave_detail_time_start is not None:
            if attendance_date.get('leave_detail_time_start') is None:
                attendance_date['leave_detail_time_start'] = one.leave_detail_time_start
            else:
                raise UserWarning("上午存在重复记录")
        if one.leave_detail_time_end is not None:
            if attendance_date.get('leave_detail_time_end') is None:
                attendance_date['leave_detail_time_end'] = one.leave_detail_time_end
            else:
                raise UserWarning("下午存在重复记录")
        if attendance_date.get(
                'leave_detail_time_start') is not None and leave_detail_ins_tmp.leave_detail_time_start is not None:
            raise UserWarning("存在重复记录，已有{date}上午的请假单".format(date=leave_detail_ins_tmp.leave_date))
        if attendance_date.get(
                'leave_detail_time_end') is not None and leave_detail_ins_tmp.leave_detail_time_end is not None:
            raise UserWarning("存在重复记录，已有{date}下午的请假单".format(date=leave_detail_ins_tmp.leave_date))
    pass  # if len(leave_detail_ins_list) == 2:  #     raise UserWarning("存在重复记录")  # elif len(leave_detail_ins_list) == 1:  #     leave_detail_ins = leave_detail_ins_list[0]  #     if leave_detail_ins.leave_detail_time_start is not None and leave_detail_ins.leave_detail_time_end is not None:  #         raise UserWarning("{date}全天存在重复记录".format(date=leave_detail_ins.leave_date))  #     else:  #         if leave_detail_ins.leave_detail_time_start is not None and leave_detail_ins_tmp.leave_detail_time_start is not None:  #             raise UserWarning("{date}上午存在重复记录".format(date=leave_detail_ins.leave_date))  #         if leave_detail_ins.leave_detail_time_end is not None and leave_detail_ins_tmp.leave_detail_time_end is not None:  #             raise UserWarning("{date}下午存在重复记录".format(date=leave_detail_ins.leave_date))  #             pass  # elif len(leave_detail_ins_list) == 0:  #     pass  # else:  #     raise UserWarning("出现异常，联系管理员")  # pass


# TODO 出差可以参考这个
# 假期拆分计算
def leave_split_cal(queryset):
    assert isinstance(queryset[0], LeaveInfo), "使用错误，不是请假界面"
    leave_detail_ins_list = []
    for leave_info_ins in queryset:
        leave_split_list = leave_split(leave_info_ins)
        if len(leave_split_list):
            leave_detail_ins_list += leave_split_list
    LeaveDetail.objects.bulk_create(leave_detail_ins_list)
    pass


# 获取 人员排班信息
def get_scheduling_info_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    scheduling_info_dict = {}
    question = Q(emp=emp_one.code) & Q(attendance_date__gte=start_date) & Q(attendance_date__lte=end_date)
    scheduling_info_dict_query = EmployeeSchedulingInfo.objects.filter(question).all().order_by(
        'attendance_date').values('attendance_date', 'shifts_name')
    for one in scheduling_info_dict_query:
        scheduling_info_dict[one['attendance_date']] = one['shifts_name']
    return scheduling_info_dict


# 获取班次信息
def get_shift_info_dict():
    shift_info_dict = {}
    shift_info_list = ShiftsInfo.objects.all()
    for one in shift_info_list:
        shift_info_dict[one.name] = one
    return shift_info_dict
    pass


def edit_attendance_distinct(edit_attendance_tmp):
    assert isinstance(edit_attendance_tmp, EditAttendance), "使用错误，不是签卡实例"
    question = Q(emp=edit_attendance_tmp.emp) & Q(
        edit_attendance_date__gte=edit_attendance_tmp.edit_attendance_date) & Q(
        edit_attendance_date__lte=edit_attendance_tmp.edit_attendance_date)
    edit_attendance_list = EditAttendance.objects.filter(question).all().order_by('edit_attendance_date')
    attendance_date = {}
    for one in edit_attendance_list:
        if one.edit_attendance_time_start is not None:
            if attendance_date.get('edit_attendance_time_start') is None:
                attendance_date['edit_attendance_time_start'] = one.edit_attendance_time_start
            else:
                raise UserWarning("上午存在重复记录")
        if one.edit_attendance_time_end is not None:
            if attendance_date.get('edit_attendance_time_end') is None:
                attendance_date['edit_attendance_time_end'] = one.edit_attendance_time_end
            else:
                raise UserWarning("下午存在重复记录")
        if attendance_date.get(
                'edit_attendance_time_start') is not None and edit_attendance_tmp.edit_attendance_time_start is not None:
            raise UserWarning("存在重复记录，已有当天上午的签卡单")
        if attendance_date.get(
                'edit_attendance_time_end') is not None and edit_attendance_tmp.edit_attendance_time_end is not None:
            raise UserWarning("存在重复记录，已有当天天下午的签卡单")
        pass
    pass


#  获取有效的签卡信息
def get_edit_attendance_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    edit_attendance_dict = {}
    question = Q(emp=emp_one.code) & Q(edit_attendance_date__gte=start_date) & Q(
        edit_attendance_date__lte=end_date) & Q(edit_attendance_status='1')
    edit_attendance_list = EditAttendance.objects.filter(question).all().order_by('edit_attendance_date')
    for one in edit_attendance_list:
        # edit_attendance_dict[one.edit_attendance_date] = one
        if edit_attendance_dict.get(one.edit_attendance_date) is None:
            edit_attendance_dict[one.edit_attendance_date] = {}
        edit_attendance_date = edit_attendance_dict[one.edit_attendance_date]
        if one.edit_attendance_time_start is not None:
            if edit_attendance_date.get('edit_attendance_time_start') is None:
                edit_attendance_date['edit_attendance_time_start'] = one.edit_attendance_time_start
                edit_attendance_date['edit_attendance_time_start_type'] = one.edit_attendance_type
            else:
                raise UserWarning("存在重复记录-{name}的{attendance_date}存在重复的签卡数据".format(name=one.emp.name,
                                                                                    attendance_date=one.edit_attendance_date))
        if one.edit_attendance_time_end is not None:
            if edit_attendance_date.get('edit_attendance_time_end') is None:
                edit_attendance_date['edit_attendance_time_end'] = one.edit_attendance_time_end
                edit_attendance_date['edit_attendance_time_end_type'] = one.edit_attendance_type
            else:
                raise UserWarning("存在重复记录-{name}的{attendance_date}存在重复的签卡数据".format(name=one.emp.name,
                                                                                    attendance_date=one.edit_attendance_date))
    return edit_attendance_dict


#  请假处理 有效识别
def get_leave_detail_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    assert end_date >= start_date, "开始时间小于等于结束时间"
    # 对 假期的 开始日期小于考勤计算的结束日期 或 假期的 结束日期大于考勤计算的起始日期
    # 此次不需要判断是否生效
    #  测试是否影响 考勤数据
    question = Q(emp=emp_one.code) & Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
    leave_info_list = LeaveInfo.objects.filter(question)
    if len(leave_info_list):
        leave_split_cal(leave_info_list)
    leave_detail_dict = {}
    question = Q(emp=emp_one.code) & Q(leave_date__gte=start_date) & Q(leave_date__lte=end_date) & Q(
        leave_info_status='1')
    leave_detail_list = LeaveDetail.objects.filter(question).all().order_by('leave_date')
    for one in leave_detail_list:
        # leave_detail_dict[one.leave_date] = one
        if leave_detail_dict.get(one.leave_date) is None:
            leave_detail_dict[one.leave_date] = {}
        if one.leave_detail_time_start is not None:
            if leave_detail_dict[one.leave_date].get('leave_detail_time_start') is None:
                leave_detail_dict[one.leave_date]['leave_detail_time_start'] = one.leave_detail_time_start
                leave_detail_dict[one.leave_date]['leave_detail_time_start_type'] = one.leave_type
            else:
                raise UserWarning("存在重复记录-{name}的{attendance_date}存在重复的请假数据".format(name=one.emp.name,
                                                                                    attendance_date=one.leave_date))
        if one.leave_detail_time_end is not None:
            if leave_detail_dict[one.leave_date].get('leave_detail_time_end') is None:
                leave_detail_dict[one.leave_date]['leave_detail_time_end'] = one.leave_detail_time_end
                leave_detail_dict[one.leave_date]['leave_detail_time_end_type'] = one.leave_type
            else:
                raise UserWarning("存在重复记录-{name}的{attendance_date}存在重复的请假数据".format(name=one.emp.name,
                                                                                    attendance_date=one.leave_date))
    #  额度更新
    # 不在考勤计算中更新, 会加长时间, 影响用户体验
    # limit_update(emp=emp_one, start_date=start_date, end_date=end_date)
    return leave_detail_dict


# 获取原始打卡数据
def get_original_card_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    original_card_dict = {}
    # attendance_card 是 日期加时间 ，只有一天的情况下，会出现问题
    question = Q(emp=emp_one.code) & Q(attendance_card__gte=start_date) & Q(
        attendance_card__lt=datetime.datetime(end_date.year, end_date.month, end_date.day) + datetime.timedelta(days=1))
    original_card_dict_list = OriginalCard.objects.filter(question).all().order_by('attendance_card').values()
    for one in original_card_dict_list:
        # 嵌套字典 【打卡日期】-【Min/Max】：打卡时间 (emp_attendance)
        if original_card_dict.get(one['attendance_card'].date()) is None:
            original_card_dict[one['attendance_card'].date()] = {}
            # 排序过，当天最小值，第一次赋值
            original_card_dict[one['attendance_card'].date()]['min'] = one['attendance_card'].time()
        emp_attendance = original_card_dict[one['attendance_card'].date()]
        # 排序过，最后一次赋值，是当天最大值
        # 需要对最大值，最小值进行判断
        emp_attendance['max'] = one['attendance_card'].time()
        pass
    return original_card_dict
    pass


# 实现 AttendanceInfo 的实例申请，以及数据处理和赋值
class ExceptionAttendanceInfo:
    """
    初始赋值后，调用 attendance_info_ins() 返回 AttendanceInfo 实例
    """

    def __init__(self, emp, attendance_date, check_in, check_out, check_in_type, check_out_type, shift_info):
        assert isinstance(shift_info, ShiftsInfo), "班次调用错误"
        self.shift_info = shift_info
        self.emp = emp
        self.attendance_date = attendance_date
        self.check_in = check_in
        self.check_out = check_out
        self.check_in_type = check_in_type
        self.check_out_type = check_out_type
        self.check_in_status = None
        self.check_out_status = None
        self.check_status = None
        self.attendance_date_status = self.shift_info.type_shift
        self._save()
        pass

    @staticmethod
    def _time_cal_return_minute(time_start, time_end):
        """
        返回 开始时间 - 结束时间 的分钟数
        :param time_start:
        :param time_end:
        :return:
        """
        assert isinstance(time_start, datetime.time), "开始时间格式错误"
        assert isinstance(time_end, datetime.time), "结束时间格式错误"
        return (time_start.hour - time_end.hour) * 60 + time_start.minute - time_end.minute

    def attendance_info_ins(self):
        attendance_info_ins = AttendanceInfo()
        dict_attendance = {'正常': '0', '迟到': '1', '早退': '2', '旷工': '3'}
        attendance_info_ins.emp = self.emp
        attendance_info_ins.attendance_date = self.attendance_date
        attendance_info_ins.check_in = self.check_in
        attendance_info_ins.check_out = self.check_out
        attendance_info_ins.check_in_type = self.check_in_type
        attendance_info_ins.check_out_type = self.check_out_type
        attendance_info_ins.check_in_status = dict_attendance.get(self.check_in_status)
        attendance_info_ins.check_out_status = dict_attendance.get(self.check_out_status)
        attendance_info_ins.check_status = self.check_status
        attendance_info_ins.attendance_date_status = self.attendance_date_status
        return attendance_info_ins
        pass

    def _save(self):
        # 节假日判断
        if self.shift_info.type_shift is False:
            self.check_out_status = '正常'
            self.check_in_status = '正常'
        else:
            # 上午判定
            if self.check_in is None:
                self.check_in_status = '旷工'
            elif self._time_cal_return_minute(self.check_in, self.shift_info.check_in) <= self.shift_info.late_time:
                self.check_in_status = '正常'
            elif (self._time_cal_return_minute(self.check_in,
                                               self.shift_info.check_in)) > self.shift_info.late_time and (
                    self._time_cal_return_minute(self.check_in,
                                                 self.shift_info.check_in) <= self.shift_info.absenteeism_time):
                self.check_in_status = '迟到'
            elif (self._time_cal_return_minute(self.check_in,
                                               self.shift_info.check_in) > self.shift_info.absenteeism_time) and (
                    self._time_cal_return_minute(self.check_in, self.shift_info.check_in_end) <= 0):
                self.check_in_status = '旷工'
            elif self._time_cal_return_minute(self.check_in, self.shift_info.check_in_end) > 0:
                self.check_in_status = '旷工'
            # 下午判定
            if self.check_out is None:
                self.check_out_status = '旷工'
            elif self._time_cal_return_minute(self.shift_info.check_out,
                                              self.check_out) <= self.shift_info.leave_early_time:
                self.check_out_status = '正常'
            elif (self._time_cal_return_minute(self.shift_info.check_out,
                                               self.check_out)) > self.shift_info.leave_early_time and (
                    self._time_cal_return_minute(self.shift_info.check_out,
                                                 self.check_out) <= self.shift_info.absenteeism_time):
                self.check_out_status = '早退'
            elif (self._time_cal_return_minute(self.shift_info.check_out,
                                               self.check_out) > self.shift_info.absenteeism_time) and (
                    self._time_cal_return_minute(self.shift_info.check_out_start, self.check_out) <= 0):
                self.check_out_status = '旷工'
            elif self._time_cal_return_minute(self.shift_info.check_out_start, self.check_out) > 0:
                self.check_out_status = '旷工'
        # 全天判断
        if self.check_in_status == '正常' and self.check_out_status == '正常':
            self.check_status = False
        else:
            self.check_status = True

    pass


# 考勤明细计算
def attendance_cal(emp_queryset, start_date, end_date):
    assert end_date >= start_date, "开始时间小于等于结束时间"
    # 获取排班信息 get_scheduling_info_dict
    # 获取班次信息 get_shift_info_dict
    # 获取签卡数据 get_edit_attendance_dict
    # 获取请假拆分后的数据 get_leave_detail_dict
    # TODO 获取出差数据
    # 获取原始打卡数据 get_original_card_dict
    # 数据整合 数据结构
    # 数据写入
    # 获取班次信息 get_shift_info_dict
    shift_info_dict = get_shift_info_dict()
    # 考勤数据列表
    attendance_info_list = []
    # 获取打卡的实例
    attendance_exception_status_card_normal = AttendanceExceptionStatus.objects.get(exception_name='打卡')
    attendance_exception_status_card_exception = AttendanceExceptionStatus.objects.get(exception_name='未打卡')
    for emp in emp_queryset:
        # 删除已存在的
        question = Q(emp=emp) & Q(attendance_date__gte=start_date) & Q(attendance_date__lte=end_date)
        AttendanceInfo.objects.filter(question).delete()
        # 获取排班信息 get_scheduling_info_dict
        scheduling_info_dict = get_scheduling_info_dict(emp, start_date, end_date)
        # 获取签卡数据 get_edit_attendance_dict
        edit_attendance_dict = get_edit_attendance_dict(emp, start_date, end_date)
        # 获取请假拆分后的数据 get_leave_detail_dict
        leave_detail_dict = get_leave_detail_dict(emp, start_date, end_date)
        # 获取原始打卡数据 get_original_card_dict
        original_card_dict = get_original_card_dict(emp, start_date, end_date)
        # 整合打卡、签卡、请假数据，赋值
        # print(scheduling_info_dict, edit_attendance_dict, leave_detail_dict, original_card_dict)
        for date, shift_name in scheduling_info_dict.items():
            check_in = None
            check_in_type = attendance_exception_status_card_exception
            check_out = None
            check_out_type = attendance_exception_status_card_exception
            # 先打卡检索
            if original_card_dict.get(date):
                # 判断原始打卡时间是否在打卡区间内
                if original_card_dict.get(date).get('min') <= shift_info_dict[shift_name].check_in_end:
                    check_in = original_card_dict.get(date).get('min')
                    check_in_type = attendance_exception_status_card_normal
                if original_card_dict.get(date).get('max') >= shift_info_dict[shift_name].check_out_start:
                    check_out = original_card_dict.get(date).get('max')
                    check_out_type = attendance_exception_status_card_normal
            # 检索签卡，如果有，覆盖
            if edit_attendance_dict.get(date):
                if edit_attendance_dict.get(date).get('edit_attendance_time_start') is not None:
                    check_in = edit_attendance_dict.get(date)['edit_attendance_time_start']
                    check_in_type = edit_attendance_dict.get(date)['edit_attendance_time_start_type']
                if edit_attendance_dict.get(date).get('edit_attendance_time_end') is not None:
                    check_out = edit_attendance_dict.get(date)['edit_attendance_time_end']
                    check_out_type = edit_attendance_dict.get(date)['edit_attendance_time_end_type']
            # 检索请假， 如果有，覆盖
            if leave_detail_dict.get(date):
                if leave_detail_dict.get(date).get('leave_detail_time_start') is not None:
                    check_in = leave_detail_dict.get(date)['leave_detail_time_start']
                    check_in_type = leave_detail_dict.get(date)['leave_detail_time_start_type']
                if leave_detail_dict.get(date).get('leave_detail_time_end') is not None:
                    check_out = leave_detail_dict.get(date)['leave_detail_time_end']
                    check_out_type = leave_detail_dict.get(date)['leave_detail_time_end_type']
            attendance_info_tmp = ExceptionAttendanceInfo(emp=emp, attendance_date=date, check_in=check_in,
                                                          check_out=check_out, check_in_type=check_in_type,
                                                          check_out_type=check_out_type,
                                                          shift_info=shift_info_dict[shift_name]).attendance_info_ins()
            assert isinstance(attendance_info_tmp, AttendanceInfo), "非 AttendanceInfo 数据实例"
            attendance_info_list.append(attendance_info_tmp)
    AttendanceInfo.objects.bulk_create(attendance_info_list)


# 考勤汇总计算
def attendance_total_cal(emp_queryset, start_date, end_date):
    assert end_date >= start_date, "开始时间小于等于结束时间"
    attendance_cal(emp_queryset, start_date, end_date)
    attendance_total_ins_list = []
    for emp in emp_queryset:
        assert isinstance(emp, EmployeeInfo), '调用错误，不是 EmployeeInfo 实例'
        # 获取年月，取得区间月份
        month = 0
        if end_date.year - start_date.year == 0:
            month = end_date.month - start_date.month
        elif end_date.year - start_date.year >= 1:
            month = end_date.month - start_date.month + (end_date.year - start_date.year) * 12
        start_date_tmp = start_date.replace(day=1)
        for num in range(month + 1):
            current_month_num = calendar.monthrange(start_date_tmp.year, start_date_tmp.month)[1]
            del_question_start = Q(emp_name=emp) & Q(section_date=start_date_tmp.strftime('%Y%m'))
            AttendanceTotal.objects.filter(del_question_start).delete()
            question = Q(emp=emp) & Q(attendance_date__gte=start_date_tmp) & Q(
                attendance_date__lte=start_date_tmp.replace(day=current_month_num))
            attendance_info_dict_list = AttendanceInfo.objects.filter(question).values()
            # check_status_choice = (('0', '正常'), ('1', '迟到'), ('2', '早退'), ('3', '旷工'))
            attendance_total_ins = attendance_total_cal_sum(emp, start_date_tmp, attendance_info_dict_list)
            attendance_total_ins_list.append(attendance_total_ins.save())
            start_date_tmp += datetime.timedelta(days=current_month_num)
    AttendanceTotal.objects.bulk_create(attendance_total_ins_list)
    pass


def attendance_total_cal_sum(emp, start_date, attendance_info_dict_list):
    arrive_total = real_arrive_total = absenteeism_total = late_total = 0
    leave_dict = {'病假': 0, '事假': 0, '年假': 0, '婚假': 0, '丧假': 0, '陪产假': 0, '产假': 0, '工伤假': 0, '探亲假': 0, '出差（请假）': 0,
                  '其他假': 0}
    for one in attendance_info_dict_list:
        # 统计考勤
        # arrive_total = arrive_total + 1 if one.get('attendance_date_status', 0) == True else 0
        if one.get('attendance_date_status'):
            arrive_total = arrive_total + 1
            if one.get('check_in_status') == '3':
                absenteeism_total = absenteeism_total + 1
            elif one.get('check_in_status') == '1':
                late_total = late_total + 1
            if one.get('check_out_status') == '3':
                absenteeism_total = absenteeism_total + 1
            elif one.get('check_out_status') == '2':
                late_total = late_total + 1
        # 统计假期
        # print(one)
        # print(one.get('check_in_type_id'), leave_dict.get(one.get('check_in_type_id'))!= None)
        if leave_dict.get(one.get('check_in_type_id')) is not None:
            leave_dict[one.get('check_in_type_id')] += 1
        # 实到天数 real_arrive_total 非请假的所有出勤天数
        elif one.get('attendance_date_status'):
            if one.get('check_in_status') != '3':
                real_arrive_total = real_arrive_total + 1
        if leave_dict.get(one.get('check_out_type_id')) is not None:
            leave_dict[one.get('check_out_type_id')] = leave_dict[one.get('check_out_type_id')] + 1
        # 实到天数 real_arrive_total 非请假的所有出勤天数
        elif one.get('attendance_date_status'):
            if one.get('check_out_status') != '3':
                real_arrive_total = real_arrive_total + 1
    # 将次数传入 ，AttendanceTotalInfo 后做转换
    sick_leave_total = leave_dict['病假']
    personal_leave_total = leave_dict['事假']
    annual_leave_total = leave_dict['年假']
    marriage_leave_total = leave_dict['婚假']
    bereavement_leave_total = leave_dict['丧假']
    paternity_leave_total = leave_dict['陪产假']
    maternity_leave_total = leave_dict['产假']
    work_related_injury_leave_total = leave_dict['工伤假']
    home_leave_total = leave_dict['探亲假']
    travelling_total = leave_dict['出差（请假）']
    other_leave_total = leave_dict['其他假']
    attendance_total_ins = AttendanceTotalInfo(emp=emp, section_date=start_date, arrive_total=arrive_total,
                                               real_arrive_total=real_arrive_total, absenteeism_total=absenteeism_total,
                                               late_total=late_total, sick_leave_total=sick_leave_total,
                                               personal_leave_total=personal_leave_total,
                                               annual_leave_total=annual_leave_total,
                                               marriage_leave_total=marriage_leave_total,
                                               bereavement_leave_total=bereavement_leave_total,
                                               paternity_leave_total=paternity_leave_total,
                                               maternity_leave_total=maternity_leave_total,
                                               work_related_injury_leave_total=work_related_injury_leave_total,
                                               home_leave_total=home_leave_total, travelling_total=travelling_total,
                                               other_leave_total=other_leave_total, )
    return attendance_total_ins
    pass


# 实现 AttendanceTotal 的实例申请，以及数据处理和赋值
class AttendanceTotalInfo:

    def __init__(self, emp, section_date, arrive_total, real_arrive_total, absenteeism_total, late_total,
                 sick_leave_total, personal_leave_total, annual_leave_total, marriage_leave_total,
                 bereavement_leave_total, paternity_leave_total, maternity_leave_total, work_related_injury_leave_total,
                 home_leave_total, travelling_total, other_leave_total, ):
        # 实到天数、 迟到不用进行处理
        self.emp_code = emp.code
        self.emp_name = emp
        self.section_date = section_date.strftime('%Y%m')
        self.arrive_total = arrive_total
        self.real_arrive_total = real_arrive_total / 2
        self.absenteeism_total = absenteeism_total / 2
        self.late_total = late_total
        self.sick_leave_total = sick_leave_total / 2
        self.personal_leave_total = personal_leave_total / 2
        self.annual_leave_total = annual_leave_total / 2
        self.marriage_leave_total = marriage_leave_total / 2
        self.bereavement_leave_total = bereavement_leave_total / 2
        self.paternity_leave_total = paternity_leave_total / 2
        self.maternity_leave_total = maternity_leave_total / 2
        self.work_related_injury_leave_total = work_related_injury_leave_total / 2
        self.home_leave_total = home_leave_total / 2
        self.travelling_total = travelling_total / 2
        self.other_leave_total = other_leave_total / 2

        pass

    def save(self):
        attendance_total_ins = AttendanceTotal()
        attendance_total_ins.emp_code = self.emp_code
        attendance_total_ins.emp_name = self.emp_name
        attendance_total_ins.section_date = self.section_date
        attendance_total_ins.arrive_total = self.arrive_total
        attendance_total_ins.real_arrive_total = self.real_arrive_total
        attendance_total_ins.absenteeism_total = self.absenteeism_total
        attendance_total_ins.late_total = self.late_total
        attendance_total_ins.sick_leave_total = self.sick_leave_total
        attendance_total_ins.personal_leave_total = self.personal_leave_total
        attendance_total_ins.annual_leave_total = self.annual_leave_total
        attendance_total_ins.marriage_leave_total = self.marriage_leave_total
        attendance_total_ins.bereavement_leave_total = self.bereavement_leave_total
        attendance_total_ins.paternity_leave_total = self.paternity_leave_total
        attendance_total_ins.maternity_leave_total = self.maternity_leave_total
        attendance_total_ins.work_related_injury_leave_total = self.work_related_injury_leave_total
        attendance_total_ins.home_leave_total = self.home_leave_total
        attendance_total_ins.travelling_total = self.travelling_total
        attendance_total_ins.other_leave_total = self.other_leave_total
        return attendance_total_ins
        pass

    pass


#  使用回调，返回日期选择的时间，参数中应该传递要使用的表单
@login_required(login_url='/admin/login/')
def form_select(request):
    assert ShareContext().path is not None, "管理站的 path 为 None"
    if request.method == 'POST':
        form = ShareContext().form(request.POST)
        print(form.is_valid())
        if form.is_valid():
            cd = form.cleaned_data
            print(cd)
            print('提交数据')
            path = ShareContext().path
            temp_argument_dict = {}
            for key, temp_dict in ShareContext().argument_dict.items():
                temp_argument_dict[key] = cd[key]
            ShareContext().callback(ShareContext().query_list, **temp_argument_dict)
            ShareContext().clear_data()
            return redirect(path)  # return redirect('http://127.0.0.1:8000/xadmin/Attendance/employeeinfo/')
    else:
        form = ShareContext().form()
        print('获取表单 {actions}'.format(actions=ShareContext().title))
    assert ShareContext().share_context is not None, "管理站的context 为 None"
    context = ShareContext().share_context
    context.update({"form": form, "title": ShareContext().title, })
    return render(request, ShareContext().templates, context=context)


# 用户登录界面
def user_login(request):
    """
    用户登录，登录成功后返回 home_form(request)
    :param request:
    :return:
    """
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(username=cd['user'], password=cd['pwd'])
            print(user)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    # return HttpResponseRedirect(redirect_to='/index/')
                    # return HttpResponseRedirect(request.POST.get('next', '/') or '/')
                    return HttpResponseRedirect(reverse(home_form))
                else:
                    return error_404(request, '禁止访问')
            else:
                return error_404(request, '账号或密码错误')
    else:
        form = UserForm()
    return render(request, template_name='Attendance/login.html', context={'form': form})


# 用户主界面
@login_required(login_url="login")
def home_form(request):
    """
    登录后直接跳转页面， 【首页】，初次登录需要修改密码
    :param request:
    :return:
    """
    user = getattr(request, 'user', None)
    #  查询考勤数据 ,并返回结果 使用 ajax_dict 查询数据时，进行自动计算
    print(user.id)
    user_emp = EmployeeInfo.objects.filter(user_ptr_id=user.id).get()
    if user_emp.pwd_status is False:
        return change_pwd(request)
    # 使用 js 来处理
    return render(request, template_name='Attendance/home.html', context={'user_emp': user_emp, })


# 修改密码
@login_required(login_url="login")
def change_pwd(request):
    login_user = getattr(request, 'user', None)
    user_emp = EmployeeInfo.objects.filter(user_ptr_id=login_user.id).get()
    if request.method == 'POST':
        form = ChangePwdForm(request.POST)
        print(form.is_valid())
        if form.is_valid():
            cd = form.cleaned_data
            # print(cd)
            user = authenticate(username=request.user.username, password=cd['old_pwd'])
            print(user)
            if user is not None:
                if user.is_active:
                    user_emp.set_password(cd['new_pwd1'])
                    user_emp.pwd_status = True
                    user_emp.save()
                    return error_404(request, '密码已修改，请重新登录')
                else:
                    return error_404(request, '禁止访问')
            else:
                return error_404(request, '原始密码错误')
        else:
            return render(request, template_name='Attendance/change_pwd.html',
                          context={'form': form, 'error': "2次密码不一致"})
    else:
        form = ChangePwdForm()
    if user_emp.pwd_status is False:
        error_str = "首次登录，请修改密码"
    else:
        error_str = None
    return render(request, template_name='Attendance/change_pwd.html', context={'form': form, 'error': error_str, })
    pass


# 友善 404 页面
def error_404(request, error_body):
    """
    异常
    :param request:
    :param error_body: 异常原因（文本)
    :return:
    """
    return render(request, template_name='Attendance/404.html', context={'error_body': error_body, })
    pass


# 登出页面
def user_logout(request):
    """
    登出
    :param request:
    :return:
    """
    logout(request)
    return render(request, template_name='Attendance/logout.html')
    pass


# 数据查询（基于ajax）
@login_required(login_url="login")
def ajax_dict(request):
    models_dict = {'attendance_detail': AttendanceInfo, 'attendance_summary': AttendanceTotal,
                   'edit_attendance': EditAttendance, 'leave_info': LeaveInfo, 'limit': Limit,
                   'help_context': HelpContext}
    login_user = getattr(request, 'user', None)
    user_emp = EmployeeInfo.objects.filter(user_ptr_id=login_user.id).get()
    # print(request.POST.get("start_date"), request.POST.get("end_date"))
    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    attendance_detail_questions = Q(attendance_date__gte=start_date) & Q(attendance_date__lte=end_date) & Q(
        emp=user_emp)
    attendance_summary_questions = Q(
        section_date__gte=datetime.datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m')) & Q(
        section_date__lte=datetime.datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m')) & Q(emp_name=user_emp)
    edit_attendance_questions = Q(edit_attendance_date__gte=start_date) & Q(edit_attendance_date__lte=end_date) & Q(
        emp=user_emp)
    leave_info_questions = Q(emp=user_emp) & Q(end_date__gte=start_date) & Q(start_date__lte=end_date)
    # 时间段判断原理是一致的
    # leave_info_questions = Q(emp=user_emp) & ((Q(start_date__lte=end_date) & Q(start_date__gte=start_date)) | (Q(
    #     end_date__lte=end_date) & Q(end_date__gte=start_date)))
    limit_questions = Q(emp_ins=user_emp) & Q(end_date__gte=start_date) & Q(start_date__lte=end_date)
    help_context_questions = Q()
    query_key = {'attendance_detail': attendance_detail_questions, 'attendance_summary': attendance_summary_questions,
                 'edit_attendance': edit_attendance_questions, 'leave_info': leave_info_questions,
                 'limit': limit_questions, 'help_context': help_context_questions}
    order_key = {'attendance_detail': 'attendance_date', 'attendance_summary': 'section_date',
                 'edit_attendance': 'edit_attendance_date', 'leave_info': 'start_date', 'limit': 'start_date',
                 'help_context': 'edit_operate'}
    if models_dict.get(request.POST.get("title_type")):
        if request.POST.get("title_type") in ('attendance_detail', 'attendance_summary'):
            user_cal(user_emp, start_date, end_date)
        if request.POST.get("title_type") in ('leave_info', 'limit'):
            limit_update(emp=user_emp, start_date=start_date, end_date=end_date)
        attendance_list = models_dict[request.POST.get("title_type")].objects.filter(
            query_key[request.POST.get("title_type")]).order_by(order_key[request.POST.get("title_type")]).values()
    else:
        return JsonResponse([{'err': '待开发'}, ], safe=False)
    date_list = [one for one in attendance_list]
    return JsonResponse(date_list, safe=False)


def user_cal(user_emp, start_date, end_date):
    start_date_tmp = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_tmp = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    standard_earliest_start_date = (datetime.date.today().replace(day=1) + datetime.timedelta(days=-1)).replace(day=1)
    if start_date_tmp <= standard_earliest_start_date:
        start_date_tmp = standard_earliest_start_date
    if end_date_tmp >= datetime.date.today():
        end_date_tmp = datetime.date.today()
    attendance_total_cal((user_emp,), start_date=start_date_tmp, end_date=end_date_tmp)


def cal_limit(queryset, start_date, end_date):
    """
    额度创建
    :param queryset:
    :param start_date:
    :param end_date:
    :return:
    """
    assert isinstance(queryset[0], EmployeeInfo), "使用错误, 必须是 EmployeeInfo 对象"
    assert end_date >= start_date, "开始时间小于等于结束时间"
    assert LimitStatus.objects.all().exists() is True, "需要先建立假期类型, 再建立额度类型"
    annual_leave_ins = LeaveType.objects.filter(exception_name='年假').get()
    paternity_leave_ins = LeaveType.objects.filter(exception_name='陪产假').get()
    maternity_leave_ins = LeaveType.objects.filter(exception_name='产假').get()
    bereavement_leave_ins = LeaveType.objects.filter(exception_name='丧假').get()
    marriage_leave_ins = LeaveType.objects.filter(exception_name='婚假').get()
    limit_ins_list = []
    for limit_type_ins in LimitStatus.objects.all():
        for emp in queryset:
            # 如果 <入职日期> 比 <结束日期> 大, 则跳过
            if emp.enter_date >= end_date:
                continue
            # 不处理离职人员
            if '离职' in emp.emp_status:
                continue
            # 男性无产假
            if emp.gender == '0' and limit_type_ins.leave_type == maternity_leave_ins:
                continue
            # 女性无陪产假
            if emp.gender == '1' and limit_type_ins.leave_type == paternity_leave_ins:
                continue
            #  丧假/婚假需要转正之后才能有
            if emp.level.level_name in ('实习', '试用', '待转正') and limit_type_ins.leave_type in (
                    bereavement_leave_ins, marriage_leave_ins):
                continue
            # 周期为 年
            if limit_type_ins.rate == '0':
                # 基准日期 为 year-01-01
                standard_date = start_date.replace(month=1, day=1)
                tmp_start_date = standard_date
                #  结束日期为 年末最后一天
                tmp_end_date = standard_date.replace(month=12, day=31)
                #  额度类型为 年假/陪产假
                if limit_type_ins.leave_type in (annual_leave_ins, paternity_leave_ins):
                    try:
                        # 入职后一年第一天 小于 起始日期 则有年假/陪产假
                        if emp.enter_date.replace(year=emp.enter_date.year + 1) <= start_date:
                            # 年假和陪产假的起始日期为 年初第一天/入职后一年第一天 的最大值
                            if emp.enter_date.replace(year=emp.enter_date.year + 1) >= standard_date:
                                tmp_start_date = emp.enter_date.replace(year=emp.enter_date.year + 1)
                        else:
                            continue
                    # 存在 2-29 入职人员, 出错处理
                    except ValueError:
                        # 入职后一年第一天 小于 起始日期 则有年假/陪产假
                        if emp.enter_date.replace(year=emp.enter_date.year + 1, day=28) <= start_date:
                            # 年假和陪产假的起始日期为 年初第一天/入职后一年第一天 的最大值
                            if emp.enter_date.replace(year=emp.enter_date.year + 1, day=28) >= standard_date:
                                tmp_start_date = emp.enter_date.replace(year=emp.enter_date.year + 1, day=28)
                        else:
                            continue
                else:
                    # 额度类型为 产假
                    #  周期为 年 起始日期 为 年初第一天/入职第一天(取最大值)
                    if emp.enter_date >= standard_date:
                        tmp_start_date = emp.enter_date
            else:
                # 基准日期为 year-month-01
                standard_date = start_date.replace(day=1)
                tmp_start_date = standard_date
                tmp_end_date = standard_date + datetime.timedelta(
                    days=calendar.monthrange(standard_date.year, standard_date.month)[1] - 1)
            # 开始日期大于结束日期, 跳过
            if tmp_start_date > tmp_end_date:
                continue
            while standard_date <= end_date:
                question = Q(emp_ins=emp) & Q(end_date__gte=tmp_start_date) & Q(start_date__lte=tmp_end_date) & Q(
                    holiday_type=limit_type_ins.leave_type)
                #  保存 增减的数据 <limit_edit> <frequency_edit>
                try:
                    tmp_limit_ins = Limit.objects.filter(question).get()
                    tmp_limit_edit = tmp_limit_ins.limit_edit
                    tmp_frequency_edit = tmp_limit_ins.frequency_edit
                    tmp_limit_ins.delete()
                except Limit.DoesNotExist:
                    tmp_limit_edit = 0
                    tmp_frequency_edit = 0
                limit_ins = Limit()
                limit_ins.emp_ins = emp
                limit_ins.holiday_type = limit_type_ins.leave_type
                limit_ins.rate = limit_type_ins.rate
                limit_ins.start_date = tmp_start_date
                limit_ins.end_date = tmp_end_date
                if limit_type_ins.leave_type == annual_leave_ins:
                    # 年假专属公式
                    # 使用 round 四舍五入 大于 0.25 看着 0.5
                    # limit_ins.standard_limit = round((
                    #     0 if (limit_ins.end_date - limit_ins.start_date).days <0
                    #         else (limit_ins.end_date - limit_ins.start_date).days / 365 * 3 + 5 *(
                    #     0 if standard_date.year - emp.enter_date.year < 10
                    #         else 1)) * 2) / 2
                    tmp_standard_limit = 0
                    if standard_date.year - emp.enter_date.year <= 0:
                        continue
                    elif standard_date.year - emp.enter_date.year <= 1:
                        tmp_standard_limit = (emp.enter_date.replace(month=12, day=31) - emp.enter_date).days / 365 * 3
                    elif standard_date.year - emp.enter_date.year <= 9:
                        tmp_standard_limit = 3
                    elif standard_date.year - emp.enter_date.year <= 10:
                        tmp_standard_limit = (emp.enter_date.replace(month=12,
                                                                     day=31) - emp.enter_date).days / 365 * 5 + 3
                    elif standard_date.year - emp.enter_date.year > 10:
                        tmp_standard_limit = 8
                    pass
                    limit_ins.standard_limit = round(tmp_standard_limit * 2) / 2
                    limit_ins.standard_frequency = int(limit_ins.standard_limit * 2)
                else:
                    # 正常额度公式
                    limit_ins.standard_limit = limit_type_ins.standard_limit
                    limit_ins.standard_frequency = limit_type_ins.standard_frequency
                #  计算已使用的额度
                # limit_ins.used_limit = 0
                # limit_ins.used_frequency = 0
                cal_used_limit_total(limit_ins)
                limit_ins.limit_edit = tmp_limit_edit
                limit_ins.frequency_edit = tmp_frequency_edit
                limit_ins.surplus_limit = limit_ins.standard_limit + limit_ins.limit_edit - limit_ins.used_limit
                limit_ins.surplus_frequency = limit_ins.standard_frequency + limit_ins.frequency_edit - limit_ins.used_frequency
                # 批量插入, 不会检查结果是否异常
                # limit_ins.save()
                limit_ins_list.append(limit_ins)
                if limit_type_ins.rate == '0':
                    standard_date = standard_date.replace(year=standard_date.year + 1)
                else:
                    standard_date = standard_date + datetime.timedelta(
                        days=calendar.monthrange(standard_date.year, standard_date.month)[1])
                pass
    Limit.objects.bulk_create(limit_ins_list)
    pass


def cal_used_limit_total(limit_ins):
    """
    已用额度计算
    :param limit_ins:
    :return:
    """
    assert isinstance(limit_ins, Limit), "使用错误, 必须是 Limit 对象"
    leave_detail_info_question = Q(emp=limit_ins.emp_ins) & Q(leave_date__gte=limit_ins.start_date) & Q(
        leave_date__lte=limit_ins.end_date) & Q(leave_type=limit_ins.holiday_type)
    limit_ins.used_limit = sum(
        [leave_info.count_length for leave_info in LeaveDetail.objects.filter(leave_detail_info_question).all()])
    limit_ins.used_frequency = LeaveDetail.objects.filter(leave_detail_info_question).values(
        'leave_info_id').distinct().count()


#  保存假期时, 更新已用额度信息, 或报错
def limit_update(emp, start_date, end_date):
    """
    额度更新
    :param emp:
    :param start_date:
    :param end_date:
    :return:
    """
    assert isinstance(emp, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    assert end_date >= start_date, "开始时间小于等于结束时间"
    question = Q(emp_ins=emp) & Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
    # print("更新额度")
    for limit_ins in Limit.objects.filter(question).all():
        cal_used_limit_total(limit_ins)
        # print(limit_ins)
        if limit_equal(Limit.objects.get(pk=limit_ins.pk), limit_ins):
            continue
        else:
            limit_ins.save()
        pass
    pass


def check_limit_type(leave_info_ins):
    """
    检查是否存在假期额度类型, 不存在则报错
    :param leave_info_ins:
    :return:
    """
    assert isinstance(leave_info_ins, LeaveInfo), "leave_info_ins 不是 LeaveInfo 对象"
    #  没有此 假期额度类型, 则不做限制,
    try:
        LimitStatus.objects.filter(leave_type=leave_info_ins.leave_type).get()
    except LimitStatus.DoesNotExist:
        return
    # 存在此 假期额度类型, 但不存在
    question_base = Q(emp_ins=leave_info_ins.emp) & Q(holiday_type=leave_info_ins.leave_type)
    # 不检查中间月份, 原因是只有周期为年的, 才存在跨多月, 一般都是隔月
    question_start_date = question_base & Q(start_date__lte=leave_info_ins.start_date) & Q(
        end_date__gte=leave_info_ins.start_date)
    question_end_date = question_base & Q(start_date__lte=leave_info_ins.end_date) & Q(
        end_date__gte=leave_info_ins.end_date)
    try:
        Limit.objects.filter(question_start_date).get()
    except Limit.DoesNotExist:
        raise UserWarning(
            "{month}区间无 {leave_type} 类型假期额度, 请确定是否拥有此额度后, 计算 {name} 的假期额度".format(
                leave_type=leave_info_ins.leave_type,
                name=leave_info_ins.emp, month=leave_info_ins.start_date.strftime('%Y%m')))
    try:
        Limit.objects.filter(question_end_date).get()
    except Limit.DoesNotExist:
        raise UserWarning(
            "{month}区间无 {leave_type} 类型假期额度, 请确定是否拥有此额度后, 计算 {name} 的假期额度".format(
                leave_type=leave_info_ins.leave_type,
                name=leave_info_ins.emp, month=leave_info_ins.end_date.strftime('%Y%m')))
    pass


def leave_info_equal(old_leave_info_ins, new_leave_info_ins):
    """
    检查 leave_info 对象是否相同(数据上)
    :param old_leave_info_ins:
    :param new_leave_info_ins:
    :return:
    """
    assert isinstance(old_leave_info_ins, LeaveInfo), "必须为 LeaveInfo 对象"
    assert isinstance(new_leave_info_ins, LeaveInfo), "必须为 LeaveInfo 对象"
    object_list = ['emp', 'start_date', 'leave_info_time_start', 'end_date', 'leave_info_time_end', 'leave_type',
                   'leave_info_status']
    for attr in object_list:
        if not getattr(old_leave_info_ins, attr) == getattr(new_leave_info_ins, attr):
            return False
    return True


def edit_attendance_equal(old_edit_attendance_ins, new_edit_attendance_ins):
    """
    检查 edit_attendance 对象是否相同(数据上)
    :param old_edit_attendance_ins:
    :param new_edit_attendance_ins:
    :return:
    """
    assert isinstance(old_edit_attendance_ins, EditAttendance), "必须为 EditAttendance 对象"
    assert isinstance(new_edit_attendance_ins, EditAttendance), "必须为 EditAttendance 对象"
    object_list = ['emp', 'edit_attendance_date', 'edit_attendance_time_start', 'edit_attendance_time_end',
                   'edit_attendance_type', 'edit_attendance_status']
    for attr in object_list:
        if not getattr(old_edit_attendance_ins, attr) == getattr(new_edit_attendance_ins, attr):
            return False
    return True


def edit_attendance_ins_built(edit_attendance_ins):
    """
    复制一个 EditAttendance 实例对象
    :param edit_attendance_ins:
    :return:
    """
    object_list = ['id', 'emp', 'edit_attendance_date', 'edit_attendance_time_start', 'edit_attendance_time_end',
                   'edit_attendance_type', 'edit_attendance_status', 'edit_attendance_operate']
    tmp_edit_attendance_ins = EditAttendance()
    for attr in object_list:
        setattr(tmp_edit_attendance_ins, attr, getattr(edit_attendance_ins, attr))
    return tmp_edit_attendance_ins


def limit_equal(old_limit_ins, new_limit_ins):
    """
    检查 limit 对象是否相同(数据上)
    :param old_limit_ins:
    :param new_limit_ins:
    :return:
    """
    assert isinstance(old_limit_ins, Limit), "必须为 Limit 对象"
    assert isinstance(new_limit_ins, Limit), "必须为 Limit 对象"
    object_list = ['emp_ins', 'holiday_type', 'rate', 'start_date', 'end_date', 'standard_limit', 'standard_frequency',
                   'used_limit', 'used_frequency', 'limit_edit', 'frequency_edit', 'surplus_limit', 'surplus_frequency']
    for attr in object_list:
        if not getattr(old_limit_ins, attr) == getattr(new_limit_ins, attr):
            return False
    return True


def help_context(request, ID):
    get_help_context = HelpContext.objects.filter(pk=ID).get()
    return JsonResponse(get_help_context.content, safe=False)
    # return render(request, template_name='Attendance/help_context.html', context={'content': help_context, })
    pass
