from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name="home"),
    path('book/add/', views.book_create, name='book_create'),
    path('book/<int:pk>/delete/', views.book_delete, name='book_delete'),
    path('book/<int:pk>/edit/', views.book_edit, name='book_edit'),
    path('book/<int:pk>/', views.book_view, name='book_view'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('book/<int:book_id>/review/', views.review_create, name='review_create'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    path('moderation/reviews/', views.review_moderation_list, name='review_moderation'),
    path('moderation/review/<int:pk>/', views.review_moderation_view, name='review_moderation_view'),
]
