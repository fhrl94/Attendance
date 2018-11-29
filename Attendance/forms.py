import sys
from django import forms

from Attendance.models import EditAttendance, LeaveInfo, LeaveDetail


class DateSelectForm(forms.Form):
    start_date = forms.DateField(label=u"开始日期", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '开始日期', 'type': 'date', }, format='%Y-%m-%d', ))
    end_date = forms.DateField(label=u"结束日期", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '结束日期', 'type': 'date', }, format='%Y-%m-%d', ))
    pass


#   更新排班后需要重启，已完成
def get_shifts_name():
    from Attendance.models import ShiftsInfo
    query_set = ShiftsInfo.objects.filter(status='1')
    name_choices = [("", "—请选择—")]
    for one in query_set.iterator():
        name_choices.append((one.id, one.name,))
    return name_choices


class ShiftsInfoDateForm(forms.Form):
    start_date = forms.DateField(label=u"开始时间", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '开始时间', 'type': 'date', 'id': 'start_time', },
        format='%Y-%m-%d', ))
    end_date = forms.DateField(label=u"结束时间", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '结束时间', 'type': 'date', 'id': 'end_time', },
        format='%Y-%m-%d', ))
    shifts_name = forms.ChoiceField(label=u"选择班次名称", widget=forms.Select(
        attrs={'class': 'form-control', 'placeholder': '选择班次名称', 'id': 'shifts_name', }), choices=[("", "—请选择—")])

    def __init__(self, *args, **kwargs):
        super(ShiftsInfoDateForm, self).__init__(*args, **kwargs)
        # 初始化时，对选项进行更新
        self['shifts_name'].field.choices = get_shifts_name

    pass


class UserForm(forms.Form):
    user = forms.CharField(label=u"账号", max_length=20, widget=forms.TextInput(
        attrs={'class': 'user', 'placeholder': '请输入用户名', 'aria-describedby': 'sizing-addon1', }))
    pwd = forms.CharField(label=u"密码", max_length=20, widget=forms.PasswordInput(
        attrs={'class': 'user', 'placeholder': '请输入密码', 'aria-describedby': 'sizing-addon2', }))


class ChangePwdForm(forms.Form):
    old_pwd = forms.CharField(label=u"原密码", max_length=20, widget=forms.PasswordInput(
        attrs={'class': 'user', 'placeholder': '请输入原始密码', 'aria-describedby': 'sizing-addon1', }))
    new_pwd1 = forms.CharField(label=u"新密码", max_length=20, widget=forms.PasswordInput(
        attrs={'class': 'user', 'placeholder': '请输入新密码', 'aria-describedby': 'sizing-addon2', }))
    new_pwd2 = forms.CharField(label=u"确认密码", max_length=20, widget=forms.PasswordInput(
        attrs={'class': 'user', 'placeholder': '请再次输入新密码', 'aria-describedby': 'sizing-addon3', }))

    def clean(self):
        if not self.is_valid():
            raise forms.ValidationError(u"所有项都为必填项")
        elif self.cleaned_data['new_pwd1'] != self.cleaned_data['new_pwd2']:
            raise forms.ValidationError(u"两次输入的新密码不一样")
        else:
            cleaned_data = super(ChangePwdForm, self).clean()
        return cleaned_data


class EditAttendanceForm(forms.ModelForm):
    class Meta:
        model = EditAttendance
        fields = '__all__'

    def clean(self):
        super(EditAttendanceForm, self).clean()
        from Attendance.views import edit_attendance_equal
        from Attendance.views import edit_attendance_distinct
        #  重复验证
        try:
            # self.initial 为空, 说明是新增
            if not self.initial:
                edit_attendance_distinct(EditAttendance(**self.cleaned_data))
            # 无修改
            elif edit_attendance_equal(EditAttendance.objects.get(pk=self.initial['id']),
                                       EditAttendance(pk=self.initial['id'], **self.cleaned_data)) is True:
                # print("无变化")
                pass
            # 有修改
            elif edit_attendance_equal(EditAttendance.objects.get(pk=self.initial['id']),
                                       EditAttendance(pk=self.initial['id'], **self.cleaned_data)) is False:
                from Attendance.views import edit_attendance_ins_built
                tmp_edit_attendance_ins = edit_attendance_ins_built(EditAttendance.objects.get(pk=self.initial['id']))
                EditAttendance.objects.get(pk=self.initial['id']).delete()
                # 是否存在重复记录，有重复则报错
                try:
                    edit_attendance_distinct(EditAttendance(**self.cleaned_data))
                except UserWarning as e:
                    raise e
                finally:
                    # 还原删除的单据
                    EditAttendance.objects.bulk_create((tmp_edit_attendance_ins,))
            else:
                raise UserWarning("请联系管理员")
        except UserWarning:
            self.add_error(field=None, error=forms.ValidationError('保存失败，原因为：{err}'.format(err=sys.exc_info()[1])))
        except AssertionError:
            self.add_error(field=None, error=forms.ValidationError('保存失败，原因为：{err}'.format(err=sys.exc_info()[1])))
    pass


class LeaveInfoForm(forms.ModelForm):
    class Meta:
        model = LeaveInfo
        fields = '__all__'

    def clean(self):
        super(LeaveInfoForm, self).clean()
        if self.cleaned_data['start_date'] > self.cleaned_data['end_date']:
            self.add_error(field=None, error=forms.ValidationError('保存失败，原因为：开始日期必须要小于等于结束日期'))
        # 检查额度类型是否存在
        from Attendance.views import check_limit_type
        check_limit_type(LeaveInfo(**self.cleaned_data))
        # 检查 leave_info 对象是否相同(数据上)
        from Attendance.views import leave_info_equal
        from Attendance.views import leave_split
        # print(leave_info_equal(LeaveInfo.objects.get(pk=self.initial['id']), LeaveInfo(pk=self.initial['id'], **self.cleaned_data)))
        #  重复验证
        try:
            # self.initial 为空, 说明是新增
            if not self.initial:
                leave_split(LeaveInfo(**self.cleaned_data))
            # 无修改
            elif leave_info_equal(LeaveInfo.objects.get(pk=self.initial['id']),
                                  LeaveInfo(pk=self.initial['id'], **self.cleaned_data)) is True:
                # print("无变化")
                pass
            # 有修改
            elif leave_info_equal(LeaveInfo.objects.get(pk=self.initial['id']),
                                  LeaveInfo(pk=self.initial['id'], **self.cleaned_data)) is False:
                # 删除已修改单据关联的 leave_detail
                LeaveDetail.objects.filter(leave_info_id=self.initial['id']).all().delete()
                try:
                    # 拆分单据，有重复则报错
                    leave_split(LeaveInfo(**self.cleaned_data))
                except UserWarning as e:
                    #  恢复已删除 单据关联的 leave_detail (因保存时, 会自动生成,故可以不用生成)
                    LeaveDetail.objects.bulk_create(leave_split(LeaveInfo.objects.get(pk=self.initial['id'])))
                    raise e
                # print("修改")
            else:
                raise UserWarning("请联系管理员")
        except UserWarning:
            self.add_error(field=None, error=forms.ValidationError('保存失败，原因为：{err}'.format(err=sys.exc_info()[1])))
        except AssertionError:
            self.add_error(field=None, error=forms.ValidationError('保存失败，原因为：{err}'.format(err=sys.exc_info()[1])))
    pass
