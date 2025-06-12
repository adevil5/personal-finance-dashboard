# Django App Development Guide

A comprehensive guide synthesized from Django's official tutorials, focusing on best practices, conventions, and strategies for building maintainable Django applications.

## Table of Contents

1. [Project Structure and App Architecture](#project-structure-and-app-architecture)
2. [Models and Database Design](#models-and-database-design)
3. [Views, URLs, and Templates](#views-urls-and-templates)
4. [Forms and User Input](#forms-and-user-input)
5. [Testing and Quality Assurance](#testing-and-quality-assurance)
6. [Static Files and Frontend Integration](#static-files-and-frontend-integration)
7. [Admin Interface Customization](#admin-interface-customization)
8. [Reusable Apps and Package Management](#reusable-apps-and-package-management)

---

## Project Structure and App Architecture

### Core Philosophy

Django follows a "batteries-included" philosophy with a focus on modularity and reusability. Each application should be a Python package that follows explicit conventions.

### Project vs App Distinction

- **Project**: Collection of configurations and apps for a particular website
- **App**: Web application that does something specific (e.g., blog, polls, authentication)
- Apps can live anywhere on your Python path and be reused across multiple projects

### Creating a New Project

```bash
django-admin startproject projectname
```

This creates:

```
projectname/
    manage.py              # Command-line utility for project interactions
    projectname/
        __init__.py
        settings.py        # Project configuration
        urls.py           # Root URL declarations
        asgi.py           # ASGI-compatible web server entry point
        wsgi.py           # WSGI-compatible web server entry point
```

### Creating a New App

```bash
python manage.py startapp appname
```

Standard app structure:

```
appname/
    __init__.py
    admin.py              # Admin interface configuration
    apps.py               # App configuration
    migrations/           # Database migrations
        __init__.py
    models.py             # Data models
    tests.py              # Tests
    views.py              # View functions
    urls.py               # App-specific URL patterns (create manually)
```

### Key Conventions

1. **Naming**: Avoid naming conflicts with Python/Django built-ins
2. **App Registration**: Add app to `INSTALLED_APPS` in settings
3. **URL Organization**: Use `include()` for modular URL routing
4. **Code Location**: Apps can exist anywhere on Python path

### Best Practices

1. **Single Responsibility**: Each app should focus on one aspect of functionality
2. **Loose Coupling**: Apps should be as independent as possible
3. **Explicit Configuration**: Use `apps.py` for app-specific configuration
4. **Namespace URLs**: Prevent naming conflicts with URL namespacing

### URL Configuration Pattern

```python
# Project urls.py
from django.urls import include, path

urlpatterns = [
    path('polls/', include('polls.urls')),
    path('admin/', admin.site.urls),
]

# App urls.py
from django.urls import path
from . import views

app_name = 'polls'  # Namespace for URL reversal
urlpatterns = [
    path('', views.index, name='index'),
    path('<int:question_id>/', views.detail, name='detail'),
]
```

## Models and Database Design

### Core Principle: DRY (Don't Repeat Yourself)

Django follows the DRY principle - define your data model in one place and automatically derive things from it, including database schema and admin interface.

### Model Definition

Models are Python classes that subclass `django.db.models.Model`. Each model maps to a single database table.

```python
from django.db import models

class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

    def __str__(self):
        return self.question_text
```

### Field Types and Options

Common field types:

- `CharField`: Short text (requires `max_length`)
- `TextField`: Large text
- `IntegerField`, `DecimalField`: Numeric values
- `DateTimeField`, `DateField`: Temporal data
- `ForeignKey`, `ManyToManyField`: Relationships
- `BooleanField`: True/False values

Field options:

- `null=True`: Allow NULL in database
- `blank=True`: Allow empty in forms
- `default`: Default value
- `unique=True`: Enforce uniqueness
- `db_index=True`: Create database index

### Relationships

```python
# One-to-many
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

# Many-to-many
class Article(models.Model):
    publications = models.ManyToManyField(Publication)
```

### Migration Workflow

1. **Make changes** to models in `models.py`
2. **Create migrations**: `python manage.py makemigrations`
3. **Review SQL**: `python manage.py sqlmigrate app_name 0001`
4. **Apply migrations**: `python manage.py migrate`

### Best Practices

1. **Always add `__str__()` method** for human-readable representation
2. **Use verbose field names** as first positional argument
3. **Keep models focused** - one model per conceptual entity
4. **Version control migrations** - they're part of your codebase
5. **Be careful with model changes** in production

### Database Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydatabase',
        'USER': 'mydatabaseuser',
        'PASSWORD': 'mypassword',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
```

### Model Methods and Properties

Add custom methods to encapsulate business logic:

```python
class Question(models.Model):
    # ... fields ...

    def was_published_recently(self):
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now

    @property
    def choice_count(self):
        return self.choice_set.count()
```

### Admin Registration

Register models to make them editable in admin:

```python
from django.contrib import admin
from .models import Question

admin.site.register(Question)
```

## Views, URLs, and Templates

### View Philosophy

A view is a "type of web page" that serves a specific function and has a specific template. Views should be focused on returning an `HttpResponse` or raising an exception.

### Basic View Structure

```python
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

def index(request):
    return HttpResponse("Hello, world.")

def detail(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    return render(request, 'polls/detail.html', {'question': question})
```

### URL Configuration

#### Project-level URLs

```python
# mysite/urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('polls/', include('polls.urls')),
    path('admin/', admin.site.urls),
]
```

#### App-level URLs with Namespacing

```python
# polls/urls.py
from django.urls import path
from . import views

app_name = 'polls'  # Application namespace
urlpatterns = [
    path('', views.index, name='index'),
    path('<int:question_id>/', views.detail, name='detail'),
    path('<int:question_id>/vote/', views.vote, name='vote'),
]
```

### URL Pattern Types

- `<int:param>`: Matches integers
- `<str:param>`: Matches any non-empty string (default)
- `<slug:param>`: Matches slug strings
- `<uuid:param>`: Matches UUID strings
- `<path:param>`: Matches any string including path separators

### Templates

#### Template Organization

```
mysite/
    templates/              # Project-wide templates
        base.html
    polls/
        templates/
            polls/          # Namespaced app templates
                index.html
                detail.html
```

#### Template Language

```django
{# polls/templates/polls/index.html #}
{% load static %}

{% if latest_question_list %}
    <ul>
    {% for question in latest_question_list %}
        <li><a href="{% url 'polls:detail' question.id %}">{{ question.question_text }}</a></li>
    {% endfor %}
    </ul>
{% else %}
    <p>No polls are available.</p>
{% endif %}
```

### Key Concepts

1. **Separation of Concerns**: Keep views focused on logic, templates on presentation
2. **URL Namespacing**: Prevent naming conflicts between apps
3. **Template Inheritance**: Use `{% extends %}` for DRY templates
4. **Context Processors**: Automatically add variables to all templates

### Shortcuts and Best Practices

```python
# Use render() instead of manual template loading
return render(request, 'polls/index.html', context)

# Use get_object_or_404() for cleaner error handling
question = get_object_or_404(Question, pk=question_id)

# Use reverse() for URL resolution
from django.urls import reverse
return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))
```

### Generic Views

Django provides generic views for common patterns:

```python
from django.views import generic

class IndexView(generic.ListView):
    template_name = 'polls/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        return Question.objects.order_by('-pub_date')[:5]

class DetailView(generic.DetailView):
    model = Question
    template_name = 'polls/detail.html'
```

## Forms and User Input

### Form Security Fundamentals

- **Always use POST** for forms that modify server-side data
- **Include CSRF protection** with `{% csrf_token %}` in all POST forms
- **Redirect after POST** to prevent duplicate submissions

### Basic Form Pattern

#### Template

```django
<form method="post" action="{% url 'polls:vote' question.id %}">
{% csrf_token %}
    <fieldset>
        <legend>{{ question.question_text }}</legend>
        {% for choice in question.choice_set.all %}
            <input type="radio" name="choice" id="choice{{ forloop.counter }}" value="{{ choice.id }}">
            <label for="choice{{ forloop.counter }}">{{ choice.choice_text }}</label><br>
        {% endfor %}
    </fieldset>
    <input type="submit" value="Vote">
</form>
```

#### View Processing

```python
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the form with error
        return render(request, 'polls/detail.html', {
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        selected_choice.votes = F('votes') + 1
        selected_choice.save()
        # Always redirect after successful POST
        return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))
```

### Django Forms Framework

For more complex forms, use Django's forms framework:

```python
from django import forms

class QuestionForm(forms.Form):
    question_text = forms.CharField(label='Question', max_length=200)
    pub_date = forms.DateTimeField(label='Date published')

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['choice_text', 'votes']
```

### Form Processing Best Practices

1. **Validate on Both Sides**: Client-side for UX, server-side for security
2. **Handle Errors Gracefully**: Display clear error messages
3. **Use Form Classes**: For complex forms, use Django's form framework
4. **Prevent CSRF**: Never disable CSRF protection
5. **Atomic Operations**: Use database transactions for data integrity

### Key Security Points

- Forms targeting internal URLs must use CSRF protection
- Never trust user input - always validate
- Use Django's form framework for automatic escaping and validation
- Redirect after successful POST to prevent duplicate submissions

### Form Field Types

When using Django forms:

- `CharField`, `EmailField`, `URLField`: Text inputs
- `IntegerField`, `DecimalField`: Numeric inputs
- `DateField`, `DateTimeField`: Date/time inputs
- `ChoiceField`, `MultipleChoiceField`: Select inputs
- `FileField`, `ImageField`: File uploads

## Testing and Quality Assurance

### Testing Philosophy

Testing is essential for maintaining code quality and preventing regressions. Django emphasizes that "tests will save you time" and are crucial for reliable software.

### Key Testing Principles

1. **Tests don't just identify problems, they prevent them**
2. **More tests are better** - even seemingly redundant tests have value
3. **Tests make your code more attractive** to other developers
4. **Automated testing saves time** compared to manual verification

### Test Structure

```python
from django.test import TestCase
from django.utils import timezone
from .models import Question

class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        """was_published_recently() returns False for future questions."""
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)
```

### Testing Best Practices

1. **Create separate test classes** for each model or view
2. **Use descriptive test method names** that explain what is being tested
3. **Test different scenarios** - past, present, future, edge cases
4. **Test at different levels** - unit tests and integration tests
5. **Keep tests fast** - use test database, mock external services

### Test-Driven Development (TDD)

Recommended approach:

1. Write test that describes the problem
2. Run test to see it fail
3. Write minimal code to make test pass
4. Refactor and improve
5. Repeat

### Django Testing Tools

- `TestCase`: Extends unittest.TestCase with Django-specific features
- `Client`: Simulates user interactions with views
- `fixtures`: Load test data from files
- `django.test.utils`: Utilities like `override_settings`

### Testing Views

```python
from django.test import TestCase
from django.urls import reverse

class QuestionIndexViewTests(TestCase):
    def test_no_questions(self):
        """If no questions exist, display appropriate message."""
        response = self.client.get(reverse('polls:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test polls

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## Static Files and Frontend Integration

### Static Files Organization

Django distinguishes between static files (CSS, JavaScript, images) and media files (user uploads).

#### Recommended Structure

```
myproject/
    myapp/
        static/
            myapp/          # Namespaced to prevent conflicts
                css/
                    style.css
                js/
                    script.js
                images/
                    logo.png
```

### Template Integration

```django
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="{% static 'myapp/css/style.css' %}">
</head>
<body>
    <img src="{% static 'myapp/images/logo.png' %}" alt="Logo">
    <script src="{% static 'myapp/js/script.js' %}"></script>
</body>
</html>
```

### Key Settings

```python
# settings.py
STATIC_URL = '/static/'  # URL prefix for static files
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Production collection point

STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Additional static directories
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
```

### Development vs Production

#### Development

- Django serves static files automatically when `DEBUG=True`
- Uses `django.contrib.staticfiles.views.serve`
- Files served directly from app directories

#### Production

- Collect static files: `python manage.py collectstatic`
- Serve via web server (Nginx, Apache) for performance
- Use CDN for global distribution

### Best Practices

1. **Always use namespacing** to prevent file conflicts between apps
2. **Use `{% static %}` template tag** instead of hardcoded paths
3. **Organize by file type** within app static directories
4. **Version static files** in production for cache busting
5. **Optimize for production** - minify, compress, use CDN

## Admin Interface Customization

### Basic Admin Registration

```python
from django.contrib import admin
from .models import Question, Choice

admin.site.register(Question)
admin.site.register(Choice)
```

### Custom Model Admin

```python
class QuestionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['question_text']}),
        ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    list_display = ['question_text', 'pub_date', 'was_published_recently']
    list_filter = ['pub_date']
    search_fields = ['question_text']

admin.site.register(Question, QuestionAdmin)
```

### Inline Models

```python
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3  # Number of empty forms to display

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
```

### Customizing Display Methods

```python
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'pub_date', 'was_published_recently']

    @admin.display(
        boolean=True,
        ordering='pub_date',
        description='Published recently?',
    )
    def was_published_recently(self, obj):
        return obj.was_published_recently()
```

### Template Customization

Override admin templates by creating templates in your project:

```
templates/
    admin/
        base_site.html      # Customize site header
        index.html          # Customize admin index
        myapp/
            change_form.html # Customize specific model forms
```

#### Example Template Override

```django
{# templates/admin/base_site.html #}
{% extends "admin/base.html" %}

{% block title %}{{ title }} | My Site Admin{% endblock %}

{% block branding %}
<h1 id="site-name"><a href="{% url 'admin:index' %}">My Site Administration</a></h1>
{% endblock %}
```

### Admin Configuration Options

- `fields`: Control field order and grouping
- `fieldsets`: Organize fields into sections
- `list_display`: Choose columns for list view
- `list_filter`: Add sidebar filters
- `search_fields`: Enable search functionality
- `ordering`: Default sort order
- `readonly_fields`: Make fields read-only
- `actions`: Add custom bulk actions

## Reusable Apps and Package Management

### Philosophy of Reusability

"Reusability is the way of life in Python." Django apps should be designed as modular, portable packages that can be shared across projects.

### Creating a Reusable App

#### 1. Package Structure

```
django-polls/
    README.rst
    LICENSE
    pyproject.toml
    MANIFEST.in
    django_polls/
        __init__.py
        apps.py
        models.py
        views.py
        urls.py
        templates/
        static/
```

#### 2. Essential Files

**README.rst**

```rst
=====
Polls
=====

Polls is a Django app to conduct web-based polls.

Quick start
-----------

1. Add "polls" to your INSTALLED_APPS setting::

    INSTALLED_APPS = [
        ...
        'django_polls',
    ]

2. Include the polls URLconf in your project urls.py::

    path('polls/', include('django_polls.urls')),

3. Run ``python manage.py migrate`` to create the polls models.
```

**pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "django-polls"
version = "0.1"
description = "A Django app to conduct web-based polls."
readme = "README.rst"
authors = [{name = "Your Name", email = "yourname@example.com"}]
classifiers = [
    "Environment :: Web Environment",
    "Framework :: Django",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Programming Language :: Python :: 3",
]
dependencies = ["Django>=4.2"]
```

**MANIFEST.in**

```
include LICENSE
include README.rst
recursive-include django_polls/static *
recursive-include django_polls/templates *
```

#### 3. Building and Distribution

```bash
# Build package
python -m build

# Install locally for testing
pip install -e .

# Upload to PyPI
twine upload dist/*
```

### Third-Party Package Evaluation

When choosing third-party packages, consider:

1. **Maintenance Status**
   - Recent updates and active development
   - Response to issues and pull requests
   - Django version compatibility

2. **Quality Indicators**
   - Documentation quality
   - Test coverage
   - Code style and organization
   - Community adoption (downloads, GitHub stars)

3. **Resources for Discovery**
   - [Django Packages](https://djangopackages.org/)
   - [PyPI](https://pypi.org/)
   - Django Forum and Discord
   - GitHub trending repositories

### Package Installation Best Practices

1. **Use Virtual Environments**

   ```bash
   python -m venv myprojectenv
   source myprojectenv/bin/activate  # On Windows: myprojectenv\Scripts\activate
   pip install django-package-name
   ```

2. **Pin Dependencies**

   ```
   # requirements.txt
   Django==4.2.0
   django-debug-toolbar==4.0.0
   ```

3. **Test Before Production**
   - Install in development environment first
   - Read documentation thoroughly
   - Check for security advisories
   - Verify licensing compatibility

### Popular Django Packages

- **django-debug-toolbar**: Development debugging
- **django-extensions**: Additional management commands
- **django-crispy-forms**: Enhanced form rendering
- **django-rest-framework**: API development
- **celery**: Asynchronous task processing
- **whitenoise**: Static file serving
- **django-environ**: Environment variable management

---

## Conclusion

This guide synthesizes Django's official tutorial wisdom into practical development strategies. Key takeaways:

### Core Principles to Remember

1. **DRY (Don't Repeat Yourself)**: Define data models once, derive everything else
2. **Modularity**: Apps should be focused, reusable, and loosely coupled
3. **Security First**: Always use CSRF protection, validate input, follow security best practices
4. **Testing is Essential**: Write tests early and often to save time and prevent bugs
5. **Convention over Configuration**: Follow Django's established patterns and naming conventions

### Development Workflow

1. **Plan** your app structure and data models
2. **Create** models with proper relationships and validation
3. **Write** tests before implementing features (TDD approach)
4. **Implement** views, URLs, and templates following separation of concerns
5. **Secure** forms with CSRF protection and proper validation
6. **Test** thoroughly at multiple levels (unit, integration, user acceptance)
7. **Document** your code and create reusable packages when appropriate

### Resources for Continued Learning

- **Official Documentation**: <https://docs.djangoproject.com/>
- **Django Packages**: <https://djangopackages.org/>
- **Django Forum**: <https://forum.djangoproject.com/>
- **Django Discord**: Community chat and support
- **Django Source Code**: Study the framework itself on GitHub

Remember: Django's "batteries-included" philosophy means most common web development needs are already solved. Focus on understanding and leveraging these built-in solutions rather than reinventing the wheel.

---

*This guide is based on Django 5.2 official tutorials and represents current best practices as of 2024.*
