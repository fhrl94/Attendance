import sys

import datetime

from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models, IntegrityError

# Create your models here.

status_choice = (('0', '未使用'), ('1', '使用中'), ('2', '已失效'))


# 人员信息

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{upload_to}/{filename}_{time}'.format(upload_to=sys.path[0] + '/upload/', filename=filename,
                                                  time=datetime.datetime.today().strftime('%Y_%m_%d_%H_%M_%S'))


class EmployeeInfo(User):
    # emp_status_choice = (('0', '已离职'), ('1', '在职'), ('2', '试用'), ('3', '实习'))
    # 继承 User 在导入或新增的时候，能直接实现数据查看
    #  可以看到用户密码 的加密
    # 表的结构:
    name = models.CharField('姓名', max_length=10)
    code = models.CharField('工号', max_length=10, validators=[RegexValidator(r'^[\d]{10}')], unique=True)
    #  排班时，需要做筛选，使用书签实现
    level = models.CharField('级别', max_length=10, )
    emp_status = models.CharField('员工状态', max_length=4, )
    pwd_status = models.BooleanField('密码是否修改')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '员工基本信息'
        verbose_name_plural = verbose_name


class EmployeeInfoImport(models.Model):
    # 表的结构:
    # path_name = models.FileField('文件名称', upload_to=sys.path[0] + '/upload/%Y_%m_%d/%H', )
    path_name = models.FileField('文件名称', upload_to=user_directory_path, )
    #  获取现在的时间
    upload_time = models.DateTimeField('上传时间', unique=True, auto_now=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = '人员信息导入'
        verbose_name_plural = verbose_name


# 考勤原始数据导入存储
class OriginalCard(models.Model):
    emp = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='工号')
    attendance_card = models.DateTimeField('出勤时间')

    def __str__(self):
        return str(self.emp)

    class Meta:
        verbose_name = '原始打卡记录'
        verbose_name_plural = verbose_name


#  考勤数据上传、导入
class OriginalCardImport(models.Model):
    # 表的结构:
    # path_name = models.FileField('文件名称', upload_to=sys.path[0] + '/upload/%Y_%m_%d/%H', )
    path_name = models.FileField('文件名称', upload_to=user_directory_path, )
    #  获取现在的时间
    upload_time = models.DateTimeField('上传时间', auto_now=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = '考勤数据导入'
        verbose_name_plural = verbose_name


# 班次
class ShiftsInfo(models.Model):
    # type_shift_choice = (('0', '节假日'), ('1', '工作日'))
    # TODO 在admin的删除动作中实现标记为失效
    # TODO 初始表中应该生成 节假日班次
    # 表的结构:
    name = models.CharField('班次名称', max_length=20, unique=True)
    type_shift = models.BooleanField('是否工作日', )
    check_in = models.TimeField('上午上班时间', null=True)
    check_in_end = models.TimeField('上午打卡截止时间', null=True)
    check_out_start = models.TimeField('下午下班开始时间', null=True)
    check_out = models.TimeField('下午下班时间', null=True)
    late_time = models.PositiveIntegerField('迟到起始值（分）')
    leave_early_time = models.PositiveIntegerField('早退起始值（分）')
    absenteeism_time = models.PositiveIntegerField('旷工起始值（分）')
    operate = models.DateTimeField('操作时间', auto_now=True)
    status = models.CharField('班次状态', max_length=1, choices=status_choice)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '班次信息'
        verbose_name_plural = verbose_name


class LegalHoliday(models.Model):
    legal_holiday_name = models.CharField('法定节假日名称', max_length=20, unique=True)
    legal_holiday = models.DateField('法定节假日', unique=True)
    operate = models.DateTimeField('操作时间', auto_now=True)
    status = models.CharField('法定节假日状态', max_length=1, choices=status_choice)

    def __str__(self):
        return str(self.legal_holiday_name)

    class Meta:
        verbose_name = '法定节假日'
        verbose_name_plural = verbose_name

    pass


# 考勤排班（时间、班次、人员）
class EmployeeSchedulingInfo(models.Model):
    # 表的结构:
    emp = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='工号')
    attendance_date = models.DateField('排班日期', )
    shifts_name = models.ForeignKey(ShiftsInfo, to_field='name', on_delete=models.CASCADE, verbose_name='班次名称')
    shifts_verbose_name = models.CharField('排班名称', max_length=20, )
    operate = models.DateTimeField('排班操作日期', auto_now=True)

    def __str__(self):
        return str(self.emp)

    class Meta:
        verbose_name = '人员排班查看'
        verbose_name_plural = verbose_name
        unique_together = ('emp', 'attendance_date')


# 查看考勤及异常
class AttendanceExceptionStatus(models.Model):
    exception_name = models.CharField('考勤异常状态名称', max_length=30, unique=True)
    exception_code = models.CharField('异常编码', max_length=4, unique=True)
    exception_status = models.CharField('使用状态', choices=status_choice, max_length=2)
    exception_operate = models.DateTimeField('异常操作日期', auto_now=True)

    def __str__(self):
        return self.exception_name

    class Meta:
        verbose_name = '考勤状态类型'
        verbose_name_plural = verbose_name


# 4. 签卡(签卡类型）

class EditAttendanceType(AttendanceExceptionStatus):
    #  做外键时需要做筛选，

    # name = models.CharField('签卡原因', max_length=20, unique=True)
    # edit_attendance_type_code =  models.CharField('签卡编码', max_length=2, unique=True)
    # edit_attendance_type_status = models.CharField('是否使用', max_length=2, choices=status_choice)
    # edit_attendance_type_operate = models.DateTimeField('操作日期', auto_now=True)
    #
    # def __str__(self):
    #     return self.name
    #
    # def save(self, *args, **kwargs):
    #     AttendanceExceptionStatus.objects.get_or_create(
    #         name=self.name, exception_code=self.edit_attendance_type_code, status=self.edit_attendance_type_status)
    #     super(EditAttendanceType, self).save(*args, **kwargs) # Call the "real" save() method.

    class Meta:
        verbose_name = '签卡类型'
        verbose_name_plural = verbose_name

# TODO 约束条件应为 edit_attendance_date 中的上午下午不能存在重复值
class EditAttendance(models.Model):
    emp = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='工号')
    edit_attendance_date = models.DateField('签卡日期')
    #  一天可以有2次签卡
    edit_attendance_time_start = models.TimeField('上午签卡时间', null=True, blank=True)
    edit_attendance_time_end = models.TimeField('下午签卡时间', null=True, blank=True)
    edit_attendance_type = models.ForeignKey(EditAttendanceType, on_delete=models.CASCADE,
                                             to_field='attendanceexceptionstatus_ptr',
                                             limit_choices_to={'exception_status': '1'}, verbose_name='签卡原因')
    #  单据状态
    edit_attendance_status = models.CharField('签卡单据状态', max_length=2, choices=status_choice)
    edit_attendance_operate = models.DateTimeField('操作日期', auto_now=True)

    def __str__(self):
        return str(self.emp)

    def save(self, *args, **kwargs):
        super(EditAttendance, self).save(*args, **kwargs)  # Call the "real" save() method.
        from Attendance.views import attendance_cal
        attendance_cal((self.emp,), self.edit_attendance_date, self.edit_attendance_date)

    class Meta:
        verbose_name = '签卡信息维护'
        verbose_name_plural = verbose_name
        unique_together = ('emp', 'edit_attendance_date', 'edit_attendance_status')


# 5. 请假（请假单、请假拆分）

class LeaveType(AttendanceExceptionStatus):
    # 表的结构:
    # name = models.CharField('请假原因', max_length=20, unique=True)
    leave_type = models.BooleanField('是否带薪假')
    legal_include = models.BooleanField('是否含法定节假日')

    # leave_status = models.CharField('假期状态', max_length=2, choices=status_choice)
    # leave_type_code = models.CharField('异常编码', max_length=2, unique=True)
    # operate = models.DateTimeField('请假类型操作日期', auto_now=True)

    # def __str__(self):
    #     return self.name

    # def save(self, *args, **kwargs):
    #     AttendanceExceptionStatus.objects.get_or_create(
    #         name=self.name, exception_code=self.leave_type_code, status=self.leave_status)
    #     super(LeaveType, self).save(*args, **kwargs) # Call the "real" save() method.

    class Meta:
        verbose_name = '假期类型'
        verbose_name_plural = verbose_name


# TODO 假期额度限制

class LeaveInfo(models.Model):
    # 表的结构:
    emp = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='工号')
    start_date = models.DateField('开始日期')
    leave_info_time_start = models.TimeField('开始请假时间', )
    end_date = models.DateField('结束日期')
    leave_info_time_end = models.TimeField('结束请假时间', )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, to_field='attendanceexceptionstatus_ptr',
                                   limit_choices_to={'exception_status': '1'}, verbose_name='假期类型')
    leave_info_status = models.CharField('假期单据状态', max_length=2, choices=status_choice)
    # TODO 审批人
    leave_info_operate = models.DateTimeField('假期操作日期', auto_now=True)

    def __str__(self):
        return str(self.emp)

    def save(self, *args, **kwargs):
        #
        if self.start_date <= self.end_date:
            try:
                super(LeaveInfo, self).save(*args, **kwargs)  # Call the "real" save() method.
                from Attendance.views import attendance_cal
                attendance_cal((self.emp,), self.start_date, self.end_date)
            except IntegrityError:
                raise UserWarning('无效')
                pass
        else:
            raise UserWarning('开始日期必须要大于结束日期')

    class Meta:
        verbose_name = '假期信息维护'
        verbose_name_plural = verbose_name


class LeaveDetail(models.Model):
    emp = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='工号')
    leave_info_id = models.ForeignKey(LeaveInfo, to_field='id', on_delete=models.CASCADE, verbose_name='单据主键')
    leave_date = models.DateField('请假日期')
    leave_detail_time_start = models.TimeField('上午请假时间', null=True, blank=True)
    leave_detail_time_end = models.TimeField('下午请假时间', null=True, blank=True)
    leave_type = models.ForeignKey(LeaveType, to_field='exception_name', on_delete=models.CASCADE, verbose_name='假期类型')
    leave_info_status = models.CharField('假期单据状态', max_length=2, choices=status_choice)
    leave_detail_operate = models.DateTimeField('假期明细操作日期', auto_now=True)

    def __str__(self):
        return str(self.emp)

    class Meta:
        verbose_name = '假期明细'
        verbose_name_plural = verbose_name
        # TODO 约束条件应为 leave_date 中的上午下午不能存在重复值
        unique_together = ('emp', 'leave_date', 'leave_info_status')

    pass


# TODO 出差
class TravelingType(AttendanceExceptionStatus):
    class Meta:
        verbose_name = '出差原因'
        verbose_name_plural = verbose_name


class AttendanceInfo(models.Model):
    #   异常状况 开头数值 0为全勤状态，3为考勤异常，2为非带薪假
    # exception_status = (('00', '正常'), ('31', '迟到'), ('32', '早退'), ('33', '旷工'), ('01', '签卡'),
    #                     ('02', '年假'), ('03', '病假'), ('04', '法定节假日'), ('05', '婚假'), ('06', '丧假'),
    #                     ('07', '陪产假'), ('08', '工伤假'),('21', '事假'), ('22', '产假')), ('99', '异常')

    check_status_choice = (('0', '正常'), ('1', '迟到'), ('2', '早退'), ('3', '旷工'))

    emp = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='工号')
    attendance_date = models.DateField('考勤日期')
    check_in = models.TimeField('上班时间', null=True)
    check_out = models.TimeField('下班时间', null=True)
    check_in_type = models.ForeignKey(AttendanceExceptionStatus, to_field='exception_name', on_delete=models.CASCADE,
                                      verbose_name='上班打卡状态', related_name='check_in_type')
    check_out_type = models.ForeignKey(AttendanceExceptionStatus, to_field='exception_name', on_delete=models.CASCADE,
                                       verbose_name='下班打卡状态', related_name='check_out_type')
    check_in_status = models.CharField(verbose_name='上午考勤状态', max_length=1, choices=check_status_choice)
    check_out_status = models.CharField(verbose_name='下午考勤状态', max_length=1, choices=check_status_choice)
    check_status = models.BooleanField('是否异常')
    attendance_date_status = models.BooleanField('是否工作日')

    # check_status = models.ForeignKey(AttendanceExceptionStatus, to_field='exception_name', on_delete=models.CASCADE,
    #                                      verbose_name='当天考勤状态', related_name='check_status')

    def __str__(self):
        return str(self.emp)

    class Meta:
        verbose_name = '考勤明细查看'
        verbose_name_plural = verbose_name
        unique_together = ('emp', 'attendance_date')


class AttendanceTotal(models.Model):
    emp_code = models.CharField('工号', max_length=10, validators=[RegexValidator(r'^[\d]{10}')], )
    emp_name = models.ForeignKey(EmployeeInfo, to_field='code', on_delete=models.CASCADE, verbose_name='姓名',
                                 related_name='emp_name')
    section_date = models.CharField('汇总区间', max_length=6, validators=[RegexValidator(r'^[\d]{6}')])
    arrive_total = models.FloatField('应到天数', )
    real_arrive_total = models.FloatField('实到天数', )
    absenteeism_total = models.FloatField('旷工天数', )
    late_total = models.FloatField('迟到/早退次数', )
    sick_leave_total = models.FloatField('病假天数', )
    personal_leave_total = models.FloatField('事假天数', )
    annual_leave_total = models.FloatField('年假天数', )
    marriage_leave_total = models.FloatField('婚假天数', )
    bereavement_leave_total = models.FloatField('丧假天数', )
    paternity_leave_total = models.FloatField('陪产假天数', )
    maternity_leave_total = models.FloatField('产假天数', )
    work_related_injury_leave_total = models.FloatField('工伤假天数', )
    home_leave_total = models.FloatField('探亲假天数', )
    travelling_total = models.FloatField('出差天数', )
    other_leave_total = models.FloatField('其他假天数', )

    class Meta:
        verbose_name = '考勤信息汇总'
        verbose_name_plural = verbose_name
        unique_together = ('emp_name', 'section_date')

    pass
