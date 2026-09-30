from django import forms
class ProjectForm(forms.Form):
    name = forms.CharField(label='Nome do projeto',max_length=120,required=False)
    root = forms.CharField(label='Pasta do projeto',max_length=1000,widget=forms.TextInput(attrs={'placeholder':r'C:\Users\juanm\OneDrive\Desktop\WORKSPACE\APPS\MeuApp'}))
    confirmation = forms.CharField(required=False,widget=forms.HiddenInput())
