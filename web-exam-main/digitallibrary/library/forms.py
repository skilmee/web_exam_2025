from django import forms
from .models import Book, Role


class BookCreateForm(forms.ModelForm):
    cover = forms.FileField(required=True, label="Обложка")

    class Meta:
        model = Book
        fields = ['title', 'description', 'year', 'publisher', 'author', 'pages', 'genres']
        widgets = {
            'genres': forms.CheckboxSelectMultiple(),
        }


class BookEditForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'description', 'year', 'publisher', 'author', 'pages', 'genres']
        widgets = {
            'genres': forms.CheckboxSelectMultiple(),
        }


class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label="Логин")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    remember_me = forms.BooleanField(required=False, label="Запомнить меня")


class RegistrationForm(forms.Form):
    username = forms.CharField(label='Логин', max_length=150)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)

    last_name = forms.CharField(label='Фамилия', max_length=150)
    first_name = forms.CharField(label='Имя', max_length=150)
    middle_name = forms.CharField(label='Отчество', max_length=150, required=False)

    role = forms.ModelChoiceField(label='Роль', queryset=Role.objects.all())


class ReviewForm(forms.Form):
    RATING_CHOICES = [
        (5, 'отлично'),
        (4, 'хорошо'),
        (3, 'удовлетворительно'),
        (2, 'неудовлетворительно'),
        (1, 'плохо'),
        (0, 'ужасно'),
    ]

    rating = forms.ChoiceField(choices=RATING_CHOICES, label='Оценка', initial=5)
    text = forms.CharField(widget=forms.Textarea, label='Текст рецензии', required=False)
