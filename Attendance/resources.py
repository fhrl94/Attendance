from import_export import resources
from .models import EmployeeInfo, OriginalCard, EditAttendanceType, LeaveType, EditAttendance, LeaveInfo


class EmployeeInfoResource(resources.ModelResource):
    class Meta:
        model = EmployeeInfo  # fields = ('name', 'code', 'level', 'emp_status')  # exclude = ('id')


class OriginalCardResource(resources.ModelResource):
    class Meta:
        model = OriginalCard


class EditAttendanceTypeResource(resources.ModelResource):
    class Meta:
        model = EditAttendanceType


class EditAttendanceResource(resources.ModelResource):
    class Meta:
        model = EditAttendance


class LeaveTypeResource(resources.ModelResource):
    class Meta:
        model = LeaveType


class LeaveInfoResource(resources.ModelResource):
    class Meta:
        model = LeaveInfo
