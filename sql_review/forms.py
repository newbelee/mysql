from django import forms

from sql_review.models import SqlReviewRecord


class SqlReviewRecordForm(forms.ModelForm):
    class Meta:
        model = SqlReviewRecord
        fields = ['id', 'for_what', 'db_id', 'conn_id', 'execute_time', 'sql']
        #fields = ['id', 'pm_name', 'for_what', 'instance_group', 'instance', 'execute_time', 'sql']
