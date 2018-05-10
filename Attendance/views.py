import datetime
import xlrd
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect

# Create your views here.
from Attendance.forms import ShiftsInfoDateForm, DateSelectForm
from Attendance.models import EmployeeInfoImport, OriginalCardImport, EmployeeInfo, EmployeeSchedulingInfo, ShiftsInfo, \
    LegalHoliday, AttendanceInfo, OriginalCard, AttendanceExceptionStatus, EditAttendance, LeaveInfo, LeaveDetail


# TODO 返回友好型页面，而不是报错
class ShareContext:
    """
    共享 xadmin 数据
    """

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ShareContext, cls).__new__(cls)
        return cls.instance

    def __init__(self, context=None, path=None, query_list=None):
        if context is not None:
            self.share_context = context
        if path is not None:
            self.path = path
        if query_list is not None:
            self.query_list = query_list

    @staticmethod
    def clear_data():
        """
        清除所有私有数据
        :return:
        """
        for key in ShareContext().__dict__:
            setattr(ShareContext(), key, None)
        pass

    pass


def get_path(queryset):
    tables = [EmployeeInfoImport, OriginalCardImport]
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


def loading_data(path, table):
    name_list = []
    print(type(table._meta.fields))
    # 删除以前所有数据
    # table.objects.all().delete()
    workbook = xlrd.open_workbook(path)
    exclude_fields = ('id',)
    # 获取表的【属性】、【中文名称】
    cols = {f.name: f.verbose_name for f in table._meta.fields if f.name not in exclude_fields}
    print(cols)
    table_list = []
    for count, one in enumerate(workbook.sheet_names()):
        # TODO 多个sheet，只处理第一个
        wb_instance = workbook.sheet_by_name(one)
        table_col_index = {}
        #  获取首行的列标题，如果需要导入的没有则报错，有则保存列数
        # 获取所有的标题
        col_title = [wb_instance.cell_value(0, col) for col in range(wb_instance.ncols)]
        # 判断列标题没有重复值 （数组去除重复值后，比较数组长度）
        assert len(sorted(set(col_title), key=col_title.index)) == len(col_title)
        # 判断是否存在于字典,存在
        for key, verbose_name in cols.items():
            try:
                table_col_index[key] = col_title.index(verbose_name)
            except ValueError:
                # UserWarning as err
                # err.args[0] 获取错误的参数
                raise UserWarning("列标题不存在", verbose_name)
        print(table_col_index)
        # 读取每一行数据，并将其值赋值给 对象
        for row in range(1, wb_instance.nrows):
            table_info = table()
            code_status = None
            # TODO 根据对应的列进行赋值，检查是否出现问题
            for col, index in table_col_index.items():
                try:
                    setattr(table_info, col, wb_instance.cell_value(row, index))
                except ValueError:
                    try:
                        setattr(table_info, col, EmployeeInfo.objects.get(code=wb_instance.cell_value(row, index)))
                    except:
                        #  工号不存在则跳过
                        code_status = wb_instance.cell_value(row, index)
                        break  # raise UserWarning("工号不存在", wb_instance.cell_value(row, index))
            if code_status != None:
                print(code_status)
                name_list.append(code_status)
                continue
            else:
                # 设置主键
                # table_info.pk = row
                # TODO 进行检查
                # table_info.check()
                table_info.clean()
                table_list.append(table_info)
        table.objects.bulk_create(table_list)
    return name_list


def date_range(start_date, end_date):
    date_tmp = [start_date, ]
    # print(date_tmp[-1])
    assert date_tmp[-1] <= end_date, "开始日期大于结束日期"
    while date_tmp[-1] < end_date:
        date_tmp.append(date_tmp[-1] + datetime.timedelta(days=1))
    return date_tmp
    pass


# 排班计算
def cal_scheduling_info(request, queryset, start_date, end_date, shift_name, ):
    emp_scheduling_info_list = []
    legal_holiday_dict = {}
    # Q & = and ， | = or
    question = Q(status=1) & Q(legal_holiday__gte=start_date) & Q(legal_holiday__lte=end_date)
    # TODO 拆包
    legal_holiday_dict_list = LegalHoliday.objects.filter(question).values('legal_holiday', 'legal_holiday_name')
    for legal_holiday_dict_one in legal_holiday_dict_list:
        legal_holiday_dict[legal_holiday_dict_one['legal_holiday']] = legal_holiday_dict_one['legal_holiday_name']
    print(legal_holiday_dict)
    for one in queryset:
        for date in date_range(start_date, end_date):
            emp_scheduling_info = EmployeeSchedulingInfo()
            emp_scheduling_info.emp = EmployeeInfo.objects.get(id=one.id)
            emp_scheduling_info.attendance_date = date
            # TODO 班次选择
            # print(date)
            if date in legal_holiday_dict.keys():
                emp_scheduling_info.shifts_name = ShiftsInfo.objects.get(name='节假日班次')
                emp_scheduling_info.shifts_verbose_name = legal_holiday_dict[date]
            elif datetime.date.isoweekday(date) in (6, 7):
                emp_scheduling_info.shifts_name = ShiftsInfo.objects.get(name='节假日班次')
                emp_scheduling_info.shifts_verbose_name = emp_scheduling_info.shifts_name
            else:
                emp_scheduling_info.shifts_name = ShiftsInfo.objects.get(id=shift_name)
                emp_scheduling_info.shifts_verbose_name = emp_scheduling_info.shifts_name
            emp_scheduling_info.operate = datetime.datetime.now()
            emp_scheduling_info_list.append(emp_scheduling_info)
            pass
        pass
    EmployeeSchedulingInfo.objects.bulk_create(emp_scheduling_info_list)

    pass


# TODO 使用装饰器，返回日期选择的时间，参数中应该传递要使用的表单
# 登录验证
@login_required(login_url='/xadmin/login/')
def data_select(request):
    # 此方法是给 xadmin 中使用，不存在 get 方法
    if request.method == 'POST':
        form = ShiftsInfoDateForm(request.POST)
        print(form.is_valid())
        if form.is_valid():
            cd = form.cleaned_data
            print(cd)
            print('提交数据')
            assert ShareContext().path is not None, "管理站的 path 为 None"
            path = ShareContext().path
            # print(ShareContext().__dict__)
            cal_scheduling_info(request=request, queryset=ShareContext().query_list, start_date=cd['start_date'],
                                end_date=cd['end_date'], shift_name=cd['shifts_name'])
            ShareContext().clear_data()
            # print(ShareContext().__dict__)
            return redirect(path)  # return redirect('http://127.0.0.1:8000/xadmin/Attendance/employeeinfo/')
    else:
        form = ShiftsInfoDateForm()
        print('获取表单')
    # print(ShareContext().share_context)
    assert ShareContext().share_context is not None, "管理站的context 为 None"
    # print(ShareContext().__dict__)
    context = ShareContext().share_context
    # context= {}
    context.update({"form": form, "title": "考勤计算", })
    return render(request, 'Attendance/selected.html', context=context)


# TODO 使用装饰器，返回日期选择的时间，参数中应该传递要使用的表单
@login_required(login_url='/xadmin/login/')
def shift_swap_select(request):
    # 此方法是给 xadmin 中使用，不存在 get 方法
    if request.method == 'POST':
        form = DateSelectForm(request.POST)
        print(form.is_valid())
        if form.is_valid():
            cd = form.cleaned_data
            print(cd)
            print('提交数据')
            assert ShareContext().path is not None, "管理站的 path 为 None"
            path = ShareContext().path
            # print(ShareContext().__dict__)
            shift_swap(request=request, queryset=ShareContext().query_list, start_date=cd['start_date'],
                       end_date=cd['end_date'])
            ShareContext().clear_data()
            # print(ShareContext().__dict__)
            return redirect(path)  # return redirect('http://127.0.0.1:8000/xadmin/Attendance/employeeinfo/')
    else:
        form = DateSelectForm()
        print('获取表单')
    # print(ShareContext().share_context)
    assert ShareContext().share_context is not None, "管理站的context 为 None"
    # print(ShareContext().__dict__)
    context = ShareContext().share_context
    # context= {}
    context.update({"form": form, "title": "排班交换", })
    return render(request, 'Attendance/selected.html', context=context)


# 排班交换
def shift_swap(request, queryset, start_date, end_date, ):
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


# TODO 使用装饰器，返回日期选择的时间，参数中应该传递要使用的表单
@login_required(login_url='/xadmin/login/')
def cal_attendance_select(request):
    if request.method == 'POST':
        form = DateSelectForm(request.POST)
        print(form.is_valid())
        if form.is_valid():
            cd = form.cleaned_data
            print(cd)
            print('提交数据')
            assert ShareContext().path is not None, "管理站的 path 为 None"
            path = ShareContext().path
            # cal_attendance_info(request=request, queryset=ShareContext().query_list, start_date=cd['start_date'],
            #                     end_date=cd['end_date'])
            #  考勤计算
            attendance_cal(ShareContext().query_list, cd['start_date'], cd['end_date'])
            ShareContext().clear_data()
            return redirect(path)  # return redirect('http://127.0.0.1:8000/xadmin/Attendance/employeeinfo/')
    else:
        form = DateSelectForm()
        print('获取表单')
    assert ShareContext().share_context is not None, "管理站的context 为 None"
    context = ShareContext().share_context
    context.update({"form": form, "title": "考勤计算", })
    return render(request, 'Attendance/selected.html', context=context)


# 假期拆分
def leave_split(leave_info_ins):
    leave_detail_ins_list = []
    shift_info_dict = get_shift_info_dict()
    scheduling_info_dict = get_scheduling_info_dict(leave_info_ins.emp, leave_info_ins.start_date,
                                                    leave_info_ins.end_date)
    # question = Q(emp=leave_info_ins.emp) & Q(leave_date__gte=leave_info_ins.start_date) & Q(
    #     leave_date__lte=leave_info_ins.end_date)
    # models 中进行了关联，直接通过实例就可以了
    question = Q(leave_info_id=leave_info_ins)
    LeaveDetail.objects.filter(question).delete()
    for attendance_date, shift_name in scheduling_info_dict.items():
        # 假期类型不含节假日
        if leave_info_ins.leave_type.legal_include == False:
            # 班次为节假日，跳过
            if shift_info_dict[shift_name].type_shift == False:
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
            # 开始时间小于 check_in_end 则赋值 开始请假时间
            if leave_info_ins.leave_info_time_start <= shift_info_dict[shift_name].check_in_end:
                leave_detail_ins.leave_detail_time_start = leave_info_ins.leave_info_time_start
            # 否则为空
            else:
                leave_detail_ins.leave_detail_time_start = None
            # 开始时间大于 check_out_start 则赋值 开始请假时间
            if leave_info_ins.leave_info_time_start >= shift_info_dict[shift_name].check_out_start:
                leave_detail_ins.leave_detail_time_end = leave_info_ins.leave_info_time_start
            # 否则为空
            else:
                leave_detail_ins.leave_detail_time_end = None
        # 当前日期为结束日期
        if attendance_date == leave_info_ins.end_date:
            # 开始时间小于 check_in_end 则赋值 结束请假时间
            if leave_info_ins.leave_info_time_end <= shift_info_dict[shift_name].check_in_end:
                leave_detail_ins.leave_detail_time_start = leave_info_ins.leave_info_time_end
            # 否则为空
            else:
                leave_detail_ins.leave_detail_time_start = None
            # 开始时间大于 check_out_start 则赋值 结束请假时间
            if leave_info_ins.leave_info_time_end >= shift_info_dict[shift_name].check_out_start:
                leave_detail_ins.leave_detail_time_end = leave_info_ins.leave_info_time_end
            # 否则为空
            else:
                leave_detail_ins.leave_detail_time_end = None
        # 只有一天
        if leave_info_ins.end_date == leave_info_ins.start_date:
            # 开始时间小于 check_in_end 则赋值 结束请假时间
            if leave_info_ins.leave_info_time_start <= shift_info_dict[shift_name].check_in_end:
                leave_detail_ins.leave_detail_time_start = leave_info_ins.leave_info_time_start
            # 否则为空
            else:
                leave_detail_ins.leave_detail_time_start = None
            # 开始时间大于 check_out_start 则赋值 结束请假时间
            if leave_info_ins.leave_info_time_end >= shift_info_dict[shift_name].check_out_start:
                leave_detail_ins.leave_detail_time_end = leave_info_ins.leave_info_time_end
            # 否则为空
            else:
                leave_detail_ins.leave_detail_time_end = None
        leave_detail_ins.leave_type = leave_info_ins.leave_type
        leave_detail_ins.leave_info_status = leave_info_ins.leave_info_status
        leave_detail_ins_list.append(leave_detail_ins)
    return leave_detail_ins_list


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


def get_scheduling_info_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    scheduling_info_dict = {}
    question = Q(emp=emp_one.code) & Q(attendance_date__gte=start_date) & Q(attendance_date__lte=end_date)
    scheduling_info_dict_query = EmployeeSchedulingInfo.objects.filter(question).all().order_by(
        'attendance_date').values('attendance_date', 'shifts_name')
    for one in scheduling_info_dict_query:
        scheduling_info_dict[one['attendance_date']] = one['shifts_name']
    return scheduling_info_dict


def get_shift_info_dict():
    shift_info_dict = {}
    shift_info_list = ShiftsInfo.objects.all()
    for one in shift_info_list:
        shift_info_dict[one.name] = one
    return shift_info_dict
    pass

#  有效签卡识别
def get_edit_attendance_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    edit_attendance_dict = {}
    question = Q(emp=emp_one.code) & Q(edit_attendance_date__gte=start_date) & Q(edit_attendance_date__lte=end_date) &\
               Q(edit_attendance_status='1')
    edit_attendance_list = EditAttendance.objects.filter(question).all().order_by('edit_attendance_date')
    for one in edit_attendance_list:
        edit_attendance_dict[one.edit_attendance_date] = one
    return edit_attendance_dict

#  请假处理 有效识别
def get_leave_detail_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    # 对 假期的 开始日期小于考勤计算的结束日期 或 假期的 结束日期大于考勤计算的起始日期
    # 此次不需要判断是否生效
    question = Q(emp=emp_one.code) & (Q(start_date__lte=end_date) | Q(end_date__gte=start_date))
    leave_info_list = LeaveInfo.objects.filter(question)
    if len(leave_info_list):
        leave_split_cal(leave_info_list)
    leave_detail_dict = {}
    question = Q(emp=emp_one.code) & Q(leave_date__gte=start_date) & Q(leave_date__lte=end_date) & Q(leave_info_status='1')
    leave_detail_list = LeaveDetail.objects.filter(question).all().order_by('leave_date')
    for one in leave_detail_list:
        leave_detail_dict[one.leave_date] = one
    return leave_detail_dict


def get_original_card_dict(emp_one, start_date, end_date):
    assert isinstance(emp_one, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    original_card_dict = {}
    # attendance_card 是 日期加时间 ，只有一天的情况下，会出现问题
    question = Q(emp=emp_one.code) & Q(attendance_card__gte=start_date) & Q(attendance_card__lt=datetime.datetime(
        end_date.year, end_date.month, end_date.day) + datetime.timedelta(days=1))
    original_card_dict_list = OriginalCard.objects.filter(question).all().order_by('attendance_card').values()
    for one in original_card_dict_list:
        # 嵌套字典 【打卡日期】-【Min/Max】：打卡时间 (emp_attendance)
        if original_card_dict.get(one['attendance_card'].date()) == None:
            original_card_dict[one['attendance_card'].date()] = {}
            # 排序过，当天最小值，第一次赋值
            original_card_dict[one['attendance_card'].date()]['min'] = one['attendance_card'].time()
        emp_attendance = original_card_dict[one['attendance_card'].date()]
        # 排序过，最后一次赋值，是当天最大值
        emp_attendance['max'] = one['attendance_card'].time()
        pass
    return original_card_dict
    pass


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
        if self.shift_info.type_shift == False:
            self.check_in_status = '正常'
        else:
            if self.check_in == None:
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
                self.check_in = None
                self.check_in_status = '旷工'
                pass
        if self.shift_info.type_shift == False:
            self.check_out_status = '正常'
        else:
            if self.check_out == None:
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
                self.check_out = None
                self.check_out_status = '旷工'
                pass
        if self.check_in_status == '正常' and self.check_out_status == '正常':
            self.check_status = False
        else:
            self.check_status = True

    pass


# 拆分单据后的计算
def attendance_cal(emp_queryset, start_date, end_date):
    # 获取排班信息 get_scheduling_info_dict
    # 获取班次信息 get_shift_info_dict
    # 获取签卡数据 get_edit_attendance_dict
    # 获取请假拆分后的数据 get_leave_detail_dict
    # TODO 获取出差数据
    # 获取原始打卡数据 get_original_card_dict

    # 数据整合 数据结构
    """
    emp = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='工号')
    attendance_date = models.DateField('考勤日期')
    check_in = models.TimeField('上班时间', null=True)
    check_out = models.TimeField('下班时间', null=True)
    check_in_status = models.ForeignKey(AttendanceExceptionStatus, to_field='exception_name', on_delete=models.CASCADE,
                                        verbose_name='上午考勤状态', related_name='check_in_status')
    check_out_status = models.ForeignKey(AttendanceExceptionStatus, to_field='exception_name', on_delete=models.CASCADE,
                                         verbose_name='下午考勤状态', related_name='check_out_status')
    check_status = models.BooleanField('是否异常')
    attendance_date_status = models.BooleanField('是否工作日')
    """
    # 数据写入
    # 获取班次信息 get_shift_info_dict
    shift_info_dict = get_shift_info_dict()
    # 考勤数据列表
    attendance_info_list = []
    # 获取打卡的实例
    attendance_exception_status_card = AttendanceExceptionStatus.objects.get(exception_name='打卡')
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
        print(scheduling_info_dict, edit_attendance_dict, leave_detail_dict, original_card_dict)
        for date, shift_name in scheduling_info_dict.items():
            check_in = None
            check_in_type = attendance_exception_status_card
            check_out = None
            check_out_type = attendance_exception_status_card
            # 先打卡检索
            if original_card_dict.get(date):
                if original_card_dict.get(date).get('min'):
                    check_in = original_card_dict.get(date).get('min')
                    check_in_type = attendance_exception_status_card
                if original_card_dict.get(date).get('max'):
                    check_out = original_card_dict.get(date).get('max')
                    check_out_type = attendance_exception_status_card
            # 检索签卡，如果有，覆盖
            if edit_attendance_dict.get(date):
                if edit_attendance_dict.get(date).edit_attendance_time_start != None:
                    check_in = edit_attendance_dict.get(date).edit_attendance_time_start
                    check_in_type = edit_attendance_dict.get(date).edit_attendance_type
                if edit_attendance_dict.get(date).edit_attendance_time_end != None:
                    check_out = edit_attendance_dict.get(date).edit_attendance_time_end
                    check_out_type = edit_attendance_dict.get(date).edit_attendance_type
            # 检索请假， 如果有，覆盖
            if leave_detail_dict.get(date):
                if leave_detail_dict.get(date).leave_detail_time_start != None:
                    check_in = leave_detail_dict.get(date).leave_detail_time_start
                    check_in_type = leave_detail_dict.get(date).leave_type
                if leave_detail_dict.get(date).leave_detail_time_end != None:
                    check_out = leave_detail_dict.get(date).leave_detail_time_end
                    check_out_type = leave_detail_dict.get(date).leave_type
            attendance_info_tmp = ExceptionAttendanceInfo(emp=emp, attendance_date=date, check_in=check_in,
                                                          check_out=check_out, check_in_type=check_in_type,
                                                          check_out_type=check_out_type,
                                                          shift_info=shift_info_dict[shift_name]).attendance_info_ins()
            assert isinstance(attendance_info_tmp, AttendanceInfo), "非 AttendanceInfo 数据实例"
            attendance_info_list.append(attendance_info_tmp)
    AttendanceInfo.objects.bulk_create(attendance_info_list)
