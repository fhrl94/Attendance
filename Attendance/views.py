import datetime
import xlrd
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Max, Min
from django.shortcuts import render, redirect

# Create your views here.
from Attendance.forms import ShiftsInfoDateForm, DateSelectForm
from Attendance.models import EmployeeInfoImport, OriginalCardImport, EmployeeInfo, EmployeeSchedulingInfo, ShiftsInfo, \
    LegalHoliday, AttendanceInfo, OriginalCard, AttendanceExceptionStatus, EditAttendance, EditAttendanceType


class ShareContext():
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

    def clear_data(self):
        """
        清除所有私有数据
        :return:
        """
        for key in ShareContext().__dict__:
            setattr(ShareContext(), key, None)
        pass
    pass


def get_initial_path(table):
    try:
        path_finally_time_result = table.objects.order_by('-upload_time').all()[0]
        # 转换为字符
        path = str(path_finally_time_result.path_name)
    except IndexError:
        print("最近一次人员信息初始化失败")
        raise UserWarning("人员信息初始化失败")

def get_path(queryset):
    tables = [EmployeeInfoImport, OriginalCardImport]
    # 如果选择2个则报错
    # print(len(queryset))
    assert len(queryset) == 1 ,"只能选择一条记录"
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
    exclude_fields = ('id', )
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
                        break
                        # raise UserWarning("工号不存在", wb_instance.cell_value(row, index))
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

# def loading_data_handle(path, table):
#    """
#    1、读取 excel 表头与 table 中的字段进行比对，生成字典 【字段】： 【列号】
#    2、获取数据库中所有的值
#    3、将excel表数据读取至 字典 【emp】-【唯一值】 ：{【字段】：数据}
#    :param path:
#    :param table:
#    :return:
#    """
#
#    pass
#
# def excel_ins_get(path):
#     """
#     获取excel表第一个 sheet 实例
#     :param path:
#     :return:
#     """
#     workbook = xlrd.open_workbook(path)
#     wb_instance = workbook.sheet_by_name(workbook.sheet_names()[0])
#     return wb_instance
#     pass
#
# def excel_data_title_get(wb_instance, table):
#     """
#     获取 table 里面的列标题
#     :param wb_instance:
#     :param table:
#     :return:
#     """
#     exclude_fields = ('id',)
#     # 获取表的【属性】、【中文名称】
#     cols = {f.name: f.verbose_name for f in table._meta.fields if f.name not in exclude_fields}
#     print(cols)
#     # TODO 多个sheet，只处理第一个
#     table_col_index = {}
#     #  获取首行的列标题，如果需要导入的没有则报错，有则保存列数
#     # 获取所有的标题
#     col_title = [wb_instance.cell_value(0, col) for col in range(wb_instance.ncols)]
#     # 判断列标题没有重复值 （数组去除重复值后，比较数组长度）
#     assert len(sorted(set(col_title), key=col_title.index)) == len(col_title)
#     # 判断是否存在于字典,存在
#     for key, verbose_name in cols.items():
#         try:
#             table_col_index[key] = col_title.index(verbose_name)
#         except ValueError:
#             # UserWarning as err
#             # err.args[0] 获取错误的参数
#             raise UserWarning("列标题不存在", verbose_name)
#     print(table_col_index)
#     return table_col_index
#     pass



def date_range(start_date, end_date):
    date_tmp = [start_date,]
    # print(date_tmp[-1])
    assert date_tmp[-1] <= end_date ,"开始日期大于结束日期"
    while (date_tmp[-1] < end_date):
        date_tmp.append(date_tmp[-1] + datetime.timedelta(days=1))
    return date_tmp
    pass

# 考勤计算
def cal_scheduling_info(request, queryset, start_date, end_date, shift_name, ):
    emp_scheduling_info_list = []
    legal_holiday_dict = {}
    # Q & = and ， | = or
    question = Q(status=1) & Q(legal_holiday__gte=start_date) & Q(legal_holiday__lte=end_date)
    # TODO 拆包
    legal_holiday_dict_list = LegalHoliday.objects.filter(question).values('legal_holiday','legal_holiday_name')
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
            return redirect(path)
            # return redirect('http://127.0.0.1:8000/xadmin/Attendance/employeeinfo/')
    else:
        form = ShiftsInfoDateForm()
        print('获取表单')
    # print(ShareContext().share_context)
    assert ShareContext().share_context is not None, "管理站的context 为 None"
    # print(ShareContext().__dict__)
    context = ShareContext().share_context
    # context= {}
    context.update({"form": form,
                    "title": "考勤计算",})
    return render(request, 'Attendance/selected.html',
                      context=context)

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

def shift_swap(request, queryset, start_date, end_date,):
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
            cal_attendance_info(request=request, queryset=ShareContext().query_list, start_date=cd['start_date'],
                                end_date=cd['end_date'])
            ShareContext().clear_data()
            return redirect(path)  # return redirect('http://127.0.0.1:8000/xadmin/Attendance/employeeinfo/')
    else:
        form = DateSelectForm()
        print('获取表单')
    assert ShareContext().share_context is not None, "管理站的context 为 None"
    context = ShareContext().share_context
    context.update({"form": form, "title": "考勤计算", })
    return render(request, 'Attendance/selected.html', context=context)

def cal_attendance_info(request, queryset, start_date, end_date):
    data_list = []
    for one in queryset:
        data = exception_decision(one, start_date, end_date)
        if len(data):
            data_list += data
    AttendanceInfo.objects.bulk_create(data_list)
    pass

def original_card_get(emp, start_date, end_date):
    """

    :param emp: EmployeeInfo 对象
    :param start_date:
    :param end_date:
    :return:嵌套字典 【打卡日期】-【Min/Max】：打卡时间 (time)
    """
    assert isinstance(emp, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    original_card_dict = {}
    question = Q(emp=emp.code) & Q(attendance_card__gte=start_date) & Q(attendance_card__lte=end_date)
    original_card_dict_list = OriginalCard.objects.filter(question).all().order_by('attendance_card').values()
    for one in original_card_dict_list:
        # 嵌套字典 【打卡日期】-【Min/Max】：打卡时间 (emp_attendance)
        # print(one['attendance_card'], one['attendance_card'].date(), )
        if original_card_dict.get(one['attendance_card'].date()) == None:
            original_card_dict[one['attendance_card'].date()] = {}
            # original_card_dict[one['attendance_card'].date()]['temp'] = one['attendance_card'].time()
            # 排序过，当天最小值，第一次赋值
            original_card_dict[one['attendance_card'].date()]['min'] = one['attendance_card'].time()
        emp_attendance = original_card_dict[one['attendance_card'].date()]
        # print(emp_attendance)
        # 排序过，最后一次赋值，是当天最大值
        emp_attendance['max'] = one['attendance_card'].time()
        # if original_card_dict.get(emp_attendance['max']) == None:
        #     emp_attendance['max'] = one['attendance_card'].time()
        # else:
        #     emp_attendance['max'] = one['attendance_card'].time()
        # if time_cal_return_minute(emp_attendance['temp'], one['attendance_card'].time()) < 0:
        #     emp_attendance['temp'] = one['attendance_card'].time()
        #     # 当天最大值
        #     if emp_attendance.get('max') == None:
        #         emp_attendance['max'] ={'max': one['attendance_card'].time()}
        #     emp_attendance['max'] = one['attendance_card'].time()
        pass
    return original_card_dict
    pass

def scheduling_info_get(emp, start_date, end_date):
    """

    :param emp:
    :param start_date:
    :param end_date:
    :return: 日期 : ShiftsInfo
    """
    assert isinstance(emp, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    scheduling_info_dict = {}
    question = Q(emp=emp.code) & Q(attendance_date__gte=start_date) & Q(attendance_date__lte=end_date)
    scheduling_info_dict_query = EmployeeSchedulingInfo.objects.filter(
        question).all().order_by('attendance_date')
    for one in scheduling_info_dict_query:
        scheduling_info_dict[one.attendance_date] = one.shifts_name
    return scheduling_info_dict
    pass

def exception_decision(emp, start_date, end_date):
    exception_dict = {'旷工': AttendanceExceptionStatus.objects.get(exception_name='旷工'),
                      '正常': AttendanceExceptionStatus.objects.get(exception_name='正常'),
                      '迟到': AttendanceExceptionStatus.objects.get(exception_name='迟到'),
                      '早退': AttendanceExceptionStatus.objects.get(exception_name='早退'),
                      '异常': AttendanceExceptionStatus.objects.get(exception_name='异常'),
                      }
    assert isinstance(emp, EmployeeInfo), "emp 不是 EmployeeInfo 对象"
    check_in_status, check_out_status = '旷工', '旷工'
    check_in_tmp, check_out_tmp = None, None
    # 获取打卡信息
    emp_original_card_dict = original_card_get(emp, start_date, end_date)
    # print(emp_original_card_dict)
    # 获取排班信息
    scheduling_info_dict = scheduling_info_get(emp, start_date, end_date)
    attendance_info_ins_list = []
    question = Q(emp=emp) & Q(attendance_date__gte=start_date) & Q(attendance_date__lte=end_date)
    AttendanceInfo.objects.filter(question).all().delete()
    for date in date_range(start_date, end_date):
        attendance_info_ins = AttendanceInfo()
        attendance_info_ins.emp = emp
        attendance_info_ins.attendance_date = date
        if scheduling_info_dict.get(date) == None:
            continue
        scheduling_info = scheduling_info_dict[date]
        # 节假日判断
        if scheduling_info.type_shift == '0':
            #  没有的打卡记录
            if emp_original_card_dict.get(date) == None:
                # AttendanceInfo.objects.create(emp=emp, attendance_date=date, check_in=None, check_out=None,
                #                                      check_in_status=exception_dict["正常"],
                #                                      check_out_status=exception_dict["正常"])
                attendance_info_ins.check_in = None
                attendance_info_ins.check_out = None
                attendance_info_ins.check_in_status = exception_dict["正常"]
                attendance_info_ins.check_out_status = exception_dict["正常"]
                attendance_info_ins.check_status = exception_dict["正常"]
                attendance_info_ins_list.append(attendance_info_ins)
                continue
            emp_original_card = emp_original_card_dict[date]
            # AttendanceInfo.objects.create(
            #     emp=emp, attendance_date=date, check_in=emp_original_card.get('min'),
            #     check_out=emp_original_card.get('max'), check_in_status=exception_dict["正常"],
            #     check_out_status=exception_dict["正常"])
            attendance_info_ins.check_in = emp_original_card.get('min')
            attendance_info_ins.check_out = emp_original_card.get('max')
            attendance_info_ins.check_in_status = exception_dict["正常"]
            attendance_info_ins.check_out_status = exception_dict["正常"]
            attendance_info_ins.check_status = exception_dict["正常"]
            attendance_info_ins_list.append(attendance_info_ins)
            continue
        if emp_original_card_dict.get(date) == None:
            # AttendanceInfo.objects.create(emp=emp, attendance_date=date, check_in=None, check_out=None,
            #                                      check_in_status=exception_dict["旷工"],
            #                                      check_out_status=exception_dict["旷工"])
            attendance_info_ins.check_in = None
            attendance_info_ins.check_out = None
            attendance_info_ins.check_in_status = exception_dict["旷工"]
            attendance_info_ins.check_out_status = exception_dict["旷工"]
            attendance_info_ins.check_status = exception_dict["异常"]
            attendance_info_ins_list.append(attendance_info_ins)
            continue
        # 判定上午的考勤 ,没有则为旷工
        emp_original_card = emp_original_card_dict[date]
        if emp_original_card.get('min') == None:
            check_in_tmp = emp_original_card['min']
            check_in_status = "旷工"
        elif time_cal_return_minute(emp_original_card['min'], scheduling_info.check_in) <= scheduling_info.late_time:
            check_in_tmp = emp_original_card['min']
            check_in_status = "正常"
        elif (time_cal_return_minute(emp_original_card['min'], scheduling_info.check_in) > scheduling_info.late_time)\
                and (time_cal_return_minute(emp_original_card['min'],
                                            scheduling_info.check_in) <= scheduling_info.absenteeism_time
        ):
            check_in_tmp = emp_original_card['min']
            check_in_status = "迟到"
        elif (time_cal_return_minute(emp_original_card['min'], scheduling_info.check_in) >
              scheduling_info.absenteeism_time) and (
                time_cal_return_minute(emp_original_card['min'], scheduling_info.check_in_end) <= 0):
            check_in_tmp = emp_original_card['min']
            check_in_status = "旷工"
        elif time_cal_return_minute(emp_original_card['min'], scheduling_info.check_in_end) > 0:
            check_in_tmp = None
            check_in_status = "旷工"
        # 判定下午的考勤，没有则为旷工
        if emp_original_card.get('max') == None:
            check_out_tmp = None
            check_out_status = "旷工"
        elif time_cal_return_minute(scheduling_info.check_out, emp_original_card['max']) <= scheduling_info.leave_early_time:
            check_out_tmp = emp_original_card['max']
            check_out_status = "正常"
        elif (time_cal_return_minute(scheduling_info.check_out, emp_original_card['max']) > scheduling_info.leave_early_time)\
                and (time_cal_return_minute(scheduling_info.check_out,
                                                emp_original_card['max']) <= scheduling_info.absenteeism_time):
            check_out_tmp = emp_original_card['max']
            check_out_status = "早退"
        elif (time_cal_return_minute(scheduling_info.check_out, emp_original_card['max']) >
              scheduling_info.absenteeism_time) and (
                time_cal_return_minute(scheduling_info.check_out_start, emp_original_card['max']) <= 0):
            check_out_tmp = emp_original_card['max']
            check_out_status = "旷工"
        elif time_cal_return_minute(scheduling_info.check_out_start, emp_original_card['max']) > 0:
            check_out_tmp = None
            check_out_status = "旷工"
        # AttendanceInfo.objects.create(emp=emp, attendance_date=date,
        #     check_in=check_in_tmp, check_out=check_out_tmp, check_in_status=exception_dict[check_in_status],
        #     check_out_status=exception_dict[check_out_status])
        attendance_info_ins.check_in = check_in_tmp
        attendance_info_ins.check_out = check_out_tmp
        attendance_info_ins.check_in_status = exception_dict[check_in_status]
        attendance_info_ins.check_out_status = exception_dict[check_out_status]
        if check_in_status == '正常' and check_out_status == '正常':
            attendance_info_ins.check_status = exception_dict['正常']
        else:
            attendance_info_ins.check_status = exception_dict['异常']
        attendance_info_ins_list.append(attendance_info_ins)
        pass
    # print(attendance_info_ins_list[0].__dict__)
    return attendance_info_ins_list
    # AttendanceInfo.objects.bulk_create(attendance_info_ins_list)
    pass

def time_cal_return_minute(time_start, time_end):
    """
    返回 开始时间 - 结束时间 的分钟数
    :param time_start:
    :param time_end:
    :return:
    """
    assert isinstance(time_start, datetime.time), "开始时间格式错误"
    assert isinstance(time_end, datetime.time), "结束时间格式错误"
    return (time_start.hour - time_end.hour)*60 + time_start.minute - time_end.minute



def edit_attendance_cal(queryset):
    # TODO 将 EditAttendanceType.objects.all().values() 拆包为字典，加快计算
    # 签卡新建保存后自动计算
    assert isinstance(queryset[0], EditAttendance), "使用错误，不是签卡界面"
    for one in queryset:
        question = Q(emp=one.emp) & Q(attendance_date=one.edit_attendance_date)
        attendance_ins = AttendanceInfo.objects.filter(question).get()
        if one.edit_attendance_time_start != None:
            attendance_ins.check_in = one.edit_attendance_time_start
            attendance_ins.check_in_status = EditAttendanceType.objects.get(exception_name=one.edit_attendance_type)
        if one.edit_attendance_time_end != None:
            attendance_ins.check_out = one.edit_attendance_time_end
            attendance_ins.check_out_status = EditAttendanceType.objects.get(exception_name=one.edit_attendance_type)
        attendance_ins.save()
        pass
    pass