from django import forms
from django.db.utils import OperationalError


class DateSelectForm(forms.Form):
    start_date = forms.DateField(label=u"开始日期", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '开始日期', 'type': 'date', }, format='%Y-%m-%d', ))
    end_date = forms.DateField(label=u"结束日期", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '结束日期', 'type': 'date', }, format='%Y-%m-%d', ))
    pass


#  TODO 更新排班后需要重启
def get_shifts_name():
    from Attendance.models import ShiftsInfo
    query_set = ShiftsInfo.objects.filter(status=1)
    name_choices = [("", "—请选择—")]
    try:
        if len(query_set) == 0:
            query_set = ShiftsInfo.objects.filter(status=1)
        for one in query_set.iterator():
            name_choices.append((one.id, one.name,))
        return name_choices
    except OperationalError:
        return name_choices


class ShiftsInfoDateForm(forms.Form):
    start_date = forms.DateField(label=u"开始时间", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '开始时间', 'type': 'date', 'id': 'start_time', },
        format='%Y-%m-%d', ))
    end_date = forms.DateField(label=u"结束时间", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '结束时间', 'type': 'date', 'id': 'end_time', },
        format='%Y-%m-%d', ))
    shifts_name = forms.ChoiceField(label=u"选择班次名称", widget=forms.Select(
        attrs={'class': 'form-control', 'placeholder': '选择班次名称', 'id': 'shifts_name', }), choices=get_shifts_name())
    pass
