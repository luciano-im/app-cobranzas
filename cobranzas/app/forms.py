from datetime import datetime
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
from django.urls import reverse
from django.utils import timezone, dateformat
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from app.models import User, Customer, Sale, SaleProduct, Product


class UserModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': _('The user or password is invalid'),
        'inactive': _('Your account is not active.'),
    }


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(required=True, label=_('First name'))
    last_name = forms.CharField(required=True, label=_('Last name'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'create-user-form'
        self.helper.form_class = 'create-form'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('signup')
        self.helper.add_input(Submit('submit', _('Create User')))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name') + UserCreationForm.Meta.fields + ('is_collector', 'is_staff',)


class CustomerCreationForm(forms.ModelForm):
    collector = UserModelChoiceField(queryset=User.objects.filter(is_collector=True).order_by('first_name', 'last_name'), label=_('Collector'))

    class Meta:
        model = Customer
        fields = '__all__'


class ProductCreationForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = '__all__'


class SaleCreationForm(forms.ModelForm):
    sale_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date', 'value': dateformat.format(timezone.make_aware(datetime.today(), timezone.get_current_timezone(), True), 'Y-m-d')}), label=_('Sale Date'))
    customer = forms.ModelChoiceField(queryset=Customer.objects.order_by('name'), label=_('Customer'))
    price = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True}), label=_('Price'))
    collector = UserModelChoiceField(queryset=User.objects.order_by('first_name', 'last_name'), required=False, label=_('Collector'))
    remarks = forms.CharField(required=False, label=_('Remarks'))

    class Meta:
        model = Sale
        fields = ['sale_date', 'customer', 'collector', 'price', 'installment_amount', 'installments', 'uncollectible', 'remarks']

    def clean_sale_date(self):
        sale_date = self.cleaned_data['sale_date']
        tz = timezone.get_current_timezone()
        today_date = timezone.make_aware(datetime.today(), tz, True)

        if sale_date > today_date.date():
            raise ValidationError(_('The sale date cannot be greater than the current date!'), code='invalid',)

        return sale_date


class SaleWithPaymentsUpdateForm(forms.ModelForm):
    sale_date = forms.DateField(required=True, input_formats=('%Y-%m-%d',), widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}), label=_('Sale Date'))
    customer = forms.ModelChoiceField(queryset=Customer.objects.order_by('name'), label=_('Customer'))
    collector = UserModelChoiceField(queryset=User.objects.order_by('first_name', 'last_name'), required=False, label=_('Collector'))
    price = forms.FloatField(disabled=True, label=_('Price'))
    installment_amount = forms.FloatField(disabled=True, label=_('Installment Amount'))
    installments = forms.IntegerField(disabled=True, label=_('Installments'))
    remarks = forms.CharField(required=False, label=_('Remarks'))

    class Meta:
        model = Sale
        fields = ['sale_date', 'customer', 'collector', 'price', 'installment_amount', 'installments', 'uncollectible', 'remarks']

    def clean_sale_date(self):
        sale_date = self.cleaned_data['sale_date']
        tz = timezone.get_current_timezone()
        today_date = timezone.make_aware(datetime.today(), tz, True)

        if sale_date > today_date.date():
            raise ValidationError(_('The sale date cannot be greater than the current date!'), code='invalid',)

        return sale_date


class SaleProductCreationForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=Product.objects.exclude(id=0), widget=forms.Select(attrs={'data-dselect-search': 'true', 'data-dselect-max-height': '360px'}), required=False, label=_('Product'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

    class Meta:
        model = SaleProduct
        fields = '__all__'


class SaleWithPaymentsProductUpdateForm(forms.ModelForm):
    price = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True}), label=_('Price'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

    class Meta:
        model = SaleProduct
        fields = '__all__'


def create_saleproduct_formset(extra_forms, form, **kwargs):
    SaleProductFormSet = inlineformset_factory(
        Sale,
        SaleProduct,
        form=form,
        fields='__all__',
        extra=extra_forms,
        can_delete=True,
        absolute_max=50,
        max_num=50
    )
    return SaleProductFormSet(**kwargs)


class CustomerFilterForm(forms.Form):
    name = forms.CharField(required=False, label=_('Name'))
    city = forms.ChoiceField(choices=(('', '---------'),) + Customer.CITY, required=False, label=_('City'))
    address = forms.CharField(required=False, label=_('Address'))
    collector = UserModelChoiceField(queryset=User.objects.order_by('first_name', 'last_name'), required=False, label=_('Collector'))


class ProductFilterForm(forms.Form):

    def brand_choices():
        return [('', '---------')] + [(c, c) for c in Product.objects.exclude(id=0).values_list('brand', flat=True).distinct().order_by('brand')]

    name = forms.CharField(required=False, label=_('Name'))
    brand = forms.ChoiceField(choices=brand_choices, required=False, label=_('Brand'))
    sku = forms.CharField(required=False, label=_('SKU'))


class SaleFilterForm(forms.Form):
    id = forms.IntegerField(required=False, label=_('ID'))
    customer = forms.ModelChoiceField(queryset=Customer.objects.order_by('name'), required=False, label=_('Customer'))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('From Date'))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('To Date'))
    product = forms.ModelChoiceField(queryset=Product.objects.exclude(id=0), required=False, label=_('Product'))


class PendingBalanceFilterForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.order_by('name'), required=False, label=_('Customer'))
    city = forms.ChoiceField(choices=(('', '---------'),) + Customer.CITY, required=False, label=_('City'))
    collector = UserModelChoiceField(queryset=User.objects.order_by('first_name', 'last_name'), required=False, label=_('Collector'))


class UncollectibleSalesFilterForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.order_by('name'), required=False, label=_('Customer'))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('From Date'))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('To Date'))
