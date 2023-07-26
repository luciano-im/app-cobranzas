from django import forms
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from app.models import Customer


class CollectionForm(forms.Form):
    checked = forms.BooleanField()
    installment = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly': True}))
    installment_amount = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True, 'class': 'form-control-plaintext'}))
    paid_amount = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True, 'class': 'form-control-plaintext'}))
    amount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'payment-input'}))
    sale_id = forms.IntegerField(widget=forms.NumberInput(attrs={'disabled': True}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False


CollectionFormset = formset_factory(
    CollectionForm,
    extra=1,
    can_delete=False,
    absolute_max=1500,
    max_num=1500
)


class CollectionFilterForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), required=False, label=_('Customer'))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('From Date'))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('To Date'))