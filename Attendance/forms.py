import sys
from django import forms

from Attendance.models import EditAttendance, LeaveInfo


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
        try:
            EditAttendance.objects.get(**self.cleaned_data)
        except EditAttendance.DoesNotExist:
            try:
                from Attendance.views import edit_attendance_distinct
                edit_attendance_distinct(EditAttendance(**self.cleaned_data))
            except UserWarning:
                raise forms.ValidationError('保存失败，原因为：{err}'.format(err=sys.exc_info()[1]))
            pass

    pass


class LeaveInfoForm(forms.ModelForm):
    class Meta:
        model = LeaveInfo
        fields = '__all__'

    def clean(self):
        super(LeaveInfoForm, self).clean()
        try:
            LeaveInfo.objects.get(**self.cleaned_data)
        except LeaveInfo.DoesNotExist:
            try:
                from Attendance.views import leave_split
                leave_split(LeaveInfo(**self.cleaned_data))
            except UserWarning:
                raise forms.ValidationError('保存失败，原因为：{err}'.format(err=sys.exc_info()[1]))
            pass

    pass
