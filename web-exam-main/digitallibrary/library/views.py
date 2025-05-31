import os
import hashlib

import bleach
import markdown2

from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.db import transaction
from django.core.paginator import Paginator

from .models import Book, Cover, Genre, User, Review, ReviewStatus
from .forms import BookCreateForm, BookEditForm, LoginForm, RegistrationForm, ReviewForm
from .decorators import role_required, login_required_with_message


UPLOAD_DIR = 'library/static/library/images'


# Create your views here.
def index(request):
    books = Book.objects.all().annotate(
        avg_rating=Avg('review__rating', filter=Q(review__status__name='Одобрена')),
        review_count=Count('review', filter=Q(review__status__name='Одобрена'))
    ).order_by('-year')

    paginator = Paginator(books, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'library/index.html', {'page_obj': page_obj})


def handle_uploaded_file(f, filename):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb+") as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return path


def calculate_md5(cover_file):
    hash_md5 = hashlib.md5()
    for chunk in cover_file.chunks():
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


@role_required('administrator')
def book_create(request):
    if request.method == 'POST':
        form = BookCreateForm(request.POST, request.FILES)

        if form.is_valid():
            description = form.cleaned_data['description'].strip()
            if not description:
                form.add_error('description', 'Описание не может быть пустым.')

            cover_file = request.FILES.get('cover')
            if not cover_file:
                form.add_error('cover', 'Обложка обязательна.')
            elif not cover_file.content_type.startswith('image/'):
                form.add_error('cover', 'Файл должен быть изображением.')

            if form.errors:
                messages.error(
                    request,
                    'При сохранении данных возникла ошибка. Проверьте корректность введённых данных.'
                )
                return render(request, 'library/book_create.html', {
                    'form': form,
                    'book': {},
                    'genres': Genre.objects.all(),
                    'selected_genre_ids': form.cleaned_data.get('genres', []),
                })

            try:
                with transaction.atomic():
                    book = form.save(commit=False)
                    book.description = bleach.clean(description)
                    book.save()
                    form.save_m2m()

                    mime = cover_file.content_type
                    ext = mime.split('/')[-1]
                    filename = f"{book.id}.{ext}"
                    md5 = calculate_md5(cover_file)
                    existing = Cover.objects.filter(md5_hash=md5).first()
                    if existing:
                        filename = existing.filename
                    else:
                        handle_uploaded_file(cover_file, filename)

                    Cover.objects.create(
                        book=book,
                        filename=filename,
                        mime_type=mime,
                        md5_hash=md5,
                    )

                messages.success(request, f'Книга «{book.title}» успешно добавлена.')
                return redirect('book_view', book.id)

            except Exception:
                messages.error(
                    request,
                    'При сохранении данных возникла ошибка. Проверьте корректность введённых данных.'
                )

        else:
            messages.error(
                request,
                'При сохранении данных возникла ошибка. Проверьте корректность введённых данных.'
            )
    else:
        form = BookCreateForm()

    return render(request, 'library/book_create.html', {
        'form': form,
        'book': {},
        'genres': Genre.objects.all(),
        'selected_genre_ids': [],
    })


@role_required('administrator')
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)

    book_title = book.title

    if hasattr(book, 'cover'):
        cover = book.cover
        md5 = cover.md5_hash
        file_path = os.path.join(UPLOAD_DIR, cover.filename)

        others_using_same_md5 = Cover.objects.filter(md5_hash=md5).exclude(book=book).exists()

        if not others_using_same_md5 and os.path.isfile(file_path):
            os.remove(file_path)

    book.delete()

    messages.success(request, f'Книга «{book_title}» успешно удалена.')
    return redirect('home')


@role_required('administrator', 'moderator')
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk)

    if request.method == 'POST':
        form = BookEditForm(request.POST, instance=book)
        if form.is_valid():
            cleaned_description = bleach.clean(form.cleaned_data['description'])

            book = form.save(commit=False)
            book.description = cleaned_description
            book.save()

            form.save_m2m()

            messages.success(request, f'Книга «{book.title}» успешно обновлена.')
            return redirect('home')
    else:
        form = BookEditForm(instance=book)

    return render(request, 'library/book_edit.html', {
        'form': form,
        'book': book,
        'genres': Genre.objects.all(),
        'selected_genre_ids': list(book.genres.values_list('id', flat=True)),
    })


def book_view(request, pk):
    book = get_object_or_404(Book.objects.prefetch_related('genres'), pk=pk)

    description_html = markdown2.markdown(book.description)

    approved_reviews = Review.objects.filter(book=book, status__name='Одобрена')
    l_reviews = len(approved_reviews)
    avg_reviews = 0

    for i in approved_reviews:
        i.text = markdown2.markdown(i.text)
        avg_reviews += i.rating

    avg_reviews = 0 if l_reviews == 0 else avg_reviews / l_reviews

    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(book=book, user=request.user).first()
        if user_review is not None:
            user_review.text = markdown2.markdown(user_review.text)

    return render(request, 'library/book_view.html', {
        'book': book,
        'description_html': description_html,
        'approved_reviews': approved_reviews,
        'user_review': user_review,
        'avg_reviews': avg_reviews,
        'l_reviews': l_reviews,
    })


def user_login(request):
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data['remember_me']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                if remember_me:
                    request.session.set_expiry(43200)  # 12h = 12 * 60 * 60g

                messages.success(request, f'Добро пожаловать, {user.username}!')
                return redirect(next_url) if next_url != 'None' else redirect(reverse('home'))
            else:
                messages.error(request, 'Невозможно аутентифицироваться с указанными логином и паролем.')
    else:
        form = LoginForm()

    return render(request, 'library/login.html', {'form': form, 'next': next_url})


@login_required_with_message
def user_logout(request):
    logout(request)
    messages.success(request, "Вы успешно вышли из системы.")
    return redirect('home')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1'],
                last_name=form.cleaned_data['last_name'],
                first_name=form.cleaned_data['first_name'],
                middle_name=form.cleaned_data['middle_name'],
                role=form.cleaned_data['role'],
            )
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('home')
    else:
        form = RegistrationForm()

    return render(request, 'library/register.html', {'form': form})


@role_required('administrator', 'moderator', 'user')
def review_create(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if Review.objects.filter(book=book, user=request.user).exists():
        messages.warning(request, "Вы уже оставили рецензию для этой книги.")
        return redirect('book_view', pk=book.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            raw_text = form.cleaned_data['text']

            if not raw_text.strip():
                messages.error(request, "Текст рецензии не может быть пустым.")
                return render(request, 'library/review_form.html', {'form': form, 'book': book})

            clean_html = bleach.clean(raw_text)

            review = Review.objects.create(
                book=book,
                user=request.user,
                rating=form.cleaned_data['rating'],
                text=clean_html,
                status=ReviewStatus.objects.get(name='На рассмотрении'),
            )
            messages.success(request, "Рецензия отправлена на модерацию.")
            return redirect('book_view', pk=book.id)
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
    else:
        form = ReviewForm()

    return render(request, 'library/review_form.html', {'form': form, 'book': book})


@login_required_with_message
def my_reviews(request):
    reviews = Review.objects.select_related('book', 'status').filter(user=request.user).order_by('-created_at')

    for i in reviews:
        i.text = markdown2.markdown(i.text)

    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'library/my_reviews.html', {
        'page_obj': page_obj
    })


@role_required('administrator', 'moderator')
def review_moderation_list(request):
    reviews = (Review.objects.select_related('book', 'user')
               .filter(status__name='На рассмотрении')
               .order_by('-created_at'))

    for i in reviews:
        i.text = markdown2.markdown(i.text)

    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'library/review_moderation_list.html', {'page_obj': page_obj})


@role_required('administrator', 'moderator')
def review_moderation_view(request, pk):
    review = get_object_or_404(Review.objects.select_related('book', 'user', 'status'), pk=pk)
    review.text = markdown2.markdown(review.text)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            review.status = ReviewStatus.objects.get(name='Одобрена')
            messages.success(request, 'Рецензия одобрена.')
        elif action == 'reject':
            review.status = ReviewStatus.objects.get(name='Отклонена')
            messages.success(request, 'Рецензия отклонена.')
        review.save()
        return redirect('review_moderation')

    return render(request, 'library/review_moderation_view.html', {'review': review})
