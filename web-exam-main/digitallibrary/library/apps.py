from django.apps import AppConfig
import logging


class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'

    def ready(self):
        from django.db.utils import OperationalError, ProgrammingError
        from django.core.exceptions import AppRegistryNotReady

        try:
            from .models import Role, ReviewStatus, Genre

            roles = [
                ("administrator", "Суперпользователь, имеет полный доступ к системе"),
                ("moderator", "Может редактировать книги и модерировать рецензии"),
                ("user", "Может оставлять рецензии"),
            ]

            for name, description in roles:
                Role.objects.get_or_create(name=name, defaults={"description": description})

            statuses = [
                "На рассмотрении",
                "Одобрена",
                "Отклонена"
            ]

            for name in statuses:
                ReviewStatus.objects.get_or_create(name=name)

            genres = [
                "Художественная литература",
                "Детектив",
                "Фэнтези",
                "Научная фантастика",
                "Романтика",
                "Ужасы",
                "Триллер",
                "Исторический роман",
                "Нехудожественная литература",
                "Биография"
            ]
            for name in genres:
                Genre.objects.get_or_create(name=name)

        except (OperationalError, ProgrammingError, AppRegistryNotReady) as e:
            logging.warning(f'Skipped initial data population: {e}')
