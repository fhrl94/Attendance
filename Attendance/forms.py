from django import forms

from Attendance.models import ShiftsInfo


class DateSelectForm(forms.Form):
    start_date = forms.DateField(label=u"开始日期", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '开始日期', 'type': 'date',},
        format='%Y-%m-%d',))
    end_date = forms.DateField(label=u"结束日期", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '结束日期', 'type': 'date', },
        format='%Y-%m-%d', ))
    pass

#  TODO 涉及到查询 makemigrations 时会报错，将此表单内容注释掉
class ShiftsInfoForm(forms.Form):

    # query_set = ShiftsInfo.objects.filter(status=1).iterator()
    # # print((query_set))
    # name_choices = [("","—请选择—")]
    # for one in query_set:
    #     name_choices.append((one.id, one.name,))
    # shifts_name = forms.ChoiceField(label=u"选择班次名称", widget=forms.Select(
    #     attrs={'class': 'form-control', 'placeholder': '选择班次名称', }),choices=name_choices)

    pass

class ShiftsInfoDateForm(forms.Form):
    start_date = forms.DateField(label=u"开始时间", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '开始时间', 'type': 'date', 'id': 'start_time', },
        format='%Y-%m-%d',))
    end_date = forms.DateField(label=u"结束时间", widget=forms.DateInput(
        attrs={'class': 'form-control', 'placeholder': '结束时间', 'type': 'date', 'id': 'end_time', },
        format='%Y-%m-%d', ))
    query_set = ShiftsInfo.objects.filter(status=1).iterator()
    # print((query_set))
    name_choices = [("","—请选择—")]
    for one in query_set:
        name_choices.append((one.id, one.name,))
    shifts_name = forms.ChoiceField(label=u"选择班次名称", widget=forms.Select(
        attrs={'class': 'form-control', 'placeholder': '选择班次名称',  'id': 'shifts_name', }),choices=name_choices)
    pass