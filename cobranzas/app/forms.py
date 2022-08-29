from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import formset_factory
from django.forms.models import inlineformset_factory
from django.urls import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from app.models import User, Customer, Sale, SaleProduct, Product


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
    collector = forms.ModelChoiceField(queryset=User.objects.filter(is_collector=True))

    class Meta:
        model = Customer
        fields = '__all__'


class ProductCreationForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = '__all__'


class SaleCreationForm(forms.ModelForm):
    price = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True}))

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


class CollectionForm(forms.Form):
    checked = forms.BooleanField()
    installment = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly': True}))
    installment_amount = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True, 'class': 'form-control-plaintext'}))
    paid_amount = forms.FloatField(widget=forms.NumberInput(attrs={'readonly': True, 'class': 'form-control-plaintext'}))
    amount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'payment-input'}))
    sale_id = forms.IntegerField(widget=forms.NumberInput(attrs={'disabled': True}))
    group = forms.CharField(widget=forms.TextInput(attrs={'disabled': True}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False


CollectionFormset = formset_factory(
    CollectionForm,
    extra=1,
    can_delete=False,
    absolute_max=50,
    max_num=50
)


class CustomerFilterForm(forms.Form):
    city = forms.ChoiceField(choices=(('', '---------'),) + Customer.CITY, required=False)
    collector = forms.ModelChoiceField(queryset=User.objects.all(), required=False)