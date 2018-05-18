from import_export import resources
from .models import EmployeeInfo, OriginalCard


class EmployeeInfoResource(resources.ModelResource):

    class Meta:
        model = EmployeeInfo
        # fields = ('name', 'code', 'level', 'emp_status')
        # exclude = ('id')



class OriginalCardResource(resources.ModelResource):

    class Meta:
        model = OriginalCard
        # fields = ('name', 'code', 'level', 'emp_status')
        # exclude = ('id')