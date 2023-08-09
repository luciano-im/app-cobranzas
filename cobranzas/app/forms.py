from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms.models import inlineformset_factory
from django.urls import reverse
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'create-user-form'
        self.helper.form_class = 'create-form'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('signup')
        self.helper.add_input(Submit('submit', 'Crear Usuario'))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('is_collector',)


class CustomerCreationForm(forms.ModelForm):
    collector = forms.ModelChoiceField(queryset=User.objects.filter(is_collector=True), label=_('Collector'))

    class Meta:
        model = Customer
        fields = '__all__'


class ProductCreationForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = '__all__'


class SaleCreationForm(forms.ModelForm):
    price = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True}), label=_('Price'))

    class Meta:
        model = Sale
        fields = '__all__'


class SaleProductCreationForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

    class Meta:
        model = SaleProduct
        fields = '__all__'


SaleProductFormSet = inlineformset_factory(
    Sale,
    SaleProduct,
    form=SaleProductCreationForm,
    fields='__all__',
    extra=1,
    can_delete=False,
    absolute_max=50,
    max_num=50
)


class CustomerFilterForm(forms.Form):
    name = forms.CharField(required=False, label=_('Name'))
    city = forms.ChoiceField(choices=(('', '---------'),) + Customer.CITY, required=False, label=_('City'))
    address = forms.CharField(required=False, label=_('Address'))
    collector = UserModelChoiceField(queryset=User.objects.all(), required=False, label=_('Collector'))


class ProductFilterForm(forms.Form):

    def brand_choices():
        return [('', '---------')] + [(c, c) for c in Product.objects.values_list('brand', flat=True)]

    name = forms.CharField(required=False, label=_('Name'))
    brand = forms.ChoiceField(choices=brand_choices, required=False, label=_('Brand'))
    sku = forms.CharField(required=False, label=_('SKU'))


class SaleFilterForm(forms.Form):
    id = forms.IntegerField(required=False, label=_('ID'))
    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), required=False, label=_('Customer'))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('From Date'))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('To Date'))
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False, label=_('Product'))
