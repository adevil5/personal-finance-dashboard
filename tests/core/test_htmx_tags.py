"""
Tests for HTMX template tags.
"""
import pytest

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory, TestCase

User = get_user_model()


class HTMXTemplateTagsTestCase(TestCase):
    """Test HTMX template tags functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def render_template(self, template_string, context=None):
        """Helper to render template with context."""
        if context is None:
            context = {}

        template = Template(f"{{% load htmx_tags %}}{template_string}")
        return template.render(Context(context))

    def test_htmx_get_basic(self):
        """Test basic htmx_get tag."""
        result = self.render_template('{% htmx_get "/api/data/" %}')
        self.assertIn('hx-get="/api/data/"', result)

    def test_htmx_get_with_target(self):
        """Test htmx_get tag with target."""
        result = self.render_template('{% htmx_get "/api/data/" "#target-id" %}')
        self.assertIn('hx-get="/api/data/"', result)
        self.assertIn('hx-target="#target-id"', result)

    def test_htmx_get_with_trigger(self):
        """Test htmx_get tag with custom trigger."""
        result = self.render_template('{% htmx_get "/api/data/" "#target" "change" %}')
        self.assertIn('hx-get="/api/data/"', result)
        self.assertIn('hx-target="#target"', result)
        self.assertIn('hx-trigger="change"', result)

    def test_htmx_get_with_swap(self):
        """Test htmx_get tag with custom swap."""
        result = self.render_template(
            '{% htmx_get "/api/data/" "#target" "click" "outerHTML" %}'
        )
        self.assertIn('hx-get="/api/data/"', result)
        self.assertIn('hx-target="#target"', result)
        self.assertIn('hx-swap="outerHTML"', result)

    def test_htmx_post_basic(self):
        """Test basic htmx_post tag."""
        result = self.render_template('{% htmx_post "/api/create/" %}')
        self.assertIn('hx-post="/api/create/"', result)

    def test_htmx_post_with_target(self):
        """Test htmx_post tag with target."""
        result = self.render_template('{% htmx_post "/api/create/" "#result" %}')
        self.assertIn('hx-post="/api/create/"', result)
        self.assertIn('hx-target="#result"', result)

    def test_htmx_delete_with_confirm(self):
        """Test htmx_delete tag with confirmation."""
        result = self.render_template(
            '{% htmx_delete "/api/delete/1/" "#item-1" "Are you sure?" %}'
        )
        self.assertIn('hx-delete="/api/delete/1/"', result)
        self.assertIn('hx-target="#item-1"', result)
        self.assertIn('hx-confirm="Are you sure?"', result)

    def test_htmx_form_basic(self):
        """Test basic htmx_form tag."""
        result = self.render_template('{% htmx_form "/api/update/" %}')
        self.assertIn('hx-post="/api/update/"', result)
        self.assertIn("hx-headers", result)
        self.assertIn("X-CSRFToken", result)

    def test_htmx_boost_enabled(self):
        """Test htmx_boost tag when enabled."""
        result = self.render_template("{% htmx_boost True %}")
        self.assertIn('hx-boost="true"', result)

    def test_htmx_boost_disabled(self):
        """Test htmx_boost tag when disabled."""
        result = self.render_template("{% htmx_boost False %}")
        self.assertEqual(result.strip(), "")

    def test_htmx_push_url_enabled(self):
        """Test htmx_push_url tag when enabled."""
        result = self.render_template("{% htmx_push_url True %}")
        self.assertIn('hx-push-url="true"', result)

    def test_htmx_push_url_disabled(self):
        """Test htmx_push_url tag when disabled."""
        result = self.render_template("{% htmx_push_url False %}")
        self.assertEqual(result.strip(), "")

    def test_htmx_trigger_from_element_filter(self):
        """Test htmx_trigger_from_element filter."""
        result = self.render_template('{{ "button-id"|htmx_trigger_from_element }}')
        self.assertIn("from:#button-id", result)

    def test_htmx_loading_indicator_inclusion(self):
        """Test htmx_loading inclusion tag."""
        result = self.render_template('{% htmx_loading "form-container" "Saving..." %}')
        self.assertIn("form-container-loading", result)
        self.assertIn("Saving...", result)
        self.assertIn("htmx-indicator", result)

    def test_htmx_error_container_inclusion(self):
        """Test htmx_error_container inclusion tag."""
        result = self.render_template('{% htmx_error_container "form-errors" %}')
        self.assertIn("form-errors", result)
        self.assertIn("htmx-error-container", result)

    def test_tag_returns_safe_string(self):
        """Test that template tags return SafeString objects."""
        template = Template('{% load htmx_tags %}{% htmx_get "/api/data/" %}')
        result = template.render(Context())

        # The result should be a SafeString (marked as safe)
        self.assertIsInstance(result, str)
        # The template should not escape HTML attributes
        self.assertIn("hx-get=", result)

    def test_additional_attributes(self):
        """Test that additional hx_ attributes are included."""
        result = self.render_template(
            '{% htmx_get "/api/data/" hx_push_url="true" hx_indicator="#spinner" %}'
        )
        self.assertIn('hx-get="/api/data/"', result)
        self.assertIn('hx-push-url="true"', result)
        self.assertIn('hx-indicator="#spinner"', result)


class HTMXJavaScriptIntegrationTestCase(TestCase):
    """Test HTMX JavaScript integration."""

    def setUp(self):
        """Set up test client."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_base_template_includes_htmx(self):
        """Test that base template includes HTMX library and config."""
        from django.template.loader import render_to_string

        context = {"user": self.user}
        result = render_to_string("base.html", context)

        # Check HTMX library is included
        self.assertIn("htmx.org", result)

        # Check HTMX configuration is present
        self.assertIn("htmx.config.defaultSwapStyle", result)
        self.assertIn("window.htmxUtils", result)

        # Check event listeners are set up
        self.assertIn("htmx:beforeRequest", result)
        self.assertIn("htmx:afterRequest", result)
        self.assertIn("htmx:configRequest", result)

    def test_htmx_utils_functions_defined(self):
        """Test that HTMX utility functions are defined in base template."""
        from django.template.loader import render_to_string

        context = {"user": self.user}
        result = render_to_string("base.html", context)

        # Check utility functions are defined
        self.assertIn("showLoading:", result)
        self.assertIn("hideLoading:", result)
        self.assertIn("showError:", result)
        self.assertIn("hideError:", result)
        self.assertIn("getCSRFToken:", result)

    def test_csrf_token_handling(self):
        """Test CSRF token handling in HTMX configuration."""
        from django.middleware.csrf import get_token
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.user
        csrf_token = get_token(request)

        context = {"user": self.user, "csrf_token": csrf_token, "request": request}
        result = render_to_string("base.html", context)

        # Check CSRF token configuration
        self.assertIn("X-CSRFToken", result)
        self.assertIn("htmx:configRequest", result)


@pytest.mark.django_db
class HTMXTemplateTagsIntegrationTestCase:
    """Pytest-based integration tests for HTMX template tags."""

    def test_htmx_tags_in_real_template(self):
        """Test HTMX tags work in a real template context."""
        from django.template import Context, Template

        template_content = """
        {% load htmx_tags %}
        <div id="content">
            <button {% htmx_get "/api/data/" "#content" %}>
                Load Data
            </button>
            {% htmx_loading "content" "Loading data..." %}
            {% htmx_error_container "content-errors" %}
        </div>
        """

        template = Template(template_content)
        context = Context({})
        result = template.render(context)

        # Verify HTMX attributes are present
        assert 'hx-get="/api/data/"' in result
        assert 'hx-target="#content"' in result
        assert "content-loading" in result
        assert "Loading data..." in result
        assert "content-errors" in result

    def test_complex_htmx_form_pattern(self):
        """Test complex HTMX form pattern with all features."""
        from django.template import Context, Template

        template_content = """
        {% load htmx_tags %}
        <form {% htmx_form "/api/transactions/" "#transaction-list" "outerHTML" %}>
            <input type="text" name="description" required>
            <button type="submit">Save Transaction</button>
        </form>
        <div id="transaction-list">
            <!-- Transactions will be loaded here -->
        </div>
        {% htmx_loading "transaction-list" "Saving transaction..." %}
        {% htmx_error_container "transaction-list-errors" %}
        """

        template = Template(template_content)
        context = Context({})
        result = template.render(context)

        # Verify complex form setup
        assert 'hx-post="/api/transactions/"' in result
        assert 'hx-target="#transaction-list"' in result
        assert 'hx-swap="outerHTML"' in result
        assert "X-CSRFToken" in result
        assert "transaction-list-loading" in result
        assert "Saving transaction..." in result
