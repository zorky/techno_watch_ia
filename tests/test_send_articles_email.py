"""Tests d'intégration pour l'envoi d'emails de veille technologique."""
"""
# Tous les tests
pytest tests/test_send_articles_email.py -v

# Tests d'une classe spécifique
pytest tests/test_send_articles_email.py::TestEmailTemplateRendering -v

# Avec couverture
pytest tests/test_send_articles_email.py --cov=app.send_articles_email

# Test manuel (avec vraie config SMTP)
pytest tests/test_send_articles_email.py -m manual --no-skip
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import smtplib

from app.send_articles_email import (
    render_email_template,
    send_watch_articles,
    _send_email,
)
from app.models.emails import EmailTemplateParams


# =========================
# Fixtures
# =========================

@pytest.fixture(autouse=True)
def mock_icon_filter(monkeypatch):
    """Mock le filtre d'icônes pour éviter les erreurs de fichiers manquants."""
    def mock_load_icon(icon_name):
        return f'<svg><!-- {icon_name} --></svg>'
    
    # Si vous avez accès au module jinja_filters
    from app import jinja_filters
    if hasattr(jinja_filters, 'load_icon'):
        monkeypatch.setattr(jinja_filters, 'load_icon', mock_load_icon)
        
        
@pytest.fixture
def sample_articles():
    """Articles de test."""
    return [
        {
            'title': "L'IA révolutionne la médecine en 2025",
            'link': 'https://domain.ntld',
            'summary': 'Un résumé sur les avancées de l\'IA en médecine',
            'score': '60',
            'published': '2025-01-01T20:30:00',
            'source': 'rss'
        },
        {
            'title': "Comment l'énergie solaire transforme les villes",
            'link': 'https://domain2.ntld',
            'summary': 'Les innovations dans l\'énergie solaire urbaine',
            'score': '45',
            'published': '2025-01-02T10:15:00',
            'source': 'rss'
        },
    ]


@pytest.fixture
def email_params(sample_articles):
    """Paramètres d'email de test."""
    return EmailTemplateParams(
        articles=sample_articles,
        keywords=['ia', 'agent', 'énergie'],
        threshold=0.5
    )


# =========================
# Tests unitaires du rendu
# =========================

class TestEmailTemplateRendering:
    """Tests du rendu des templates Jinja2."""

    def test_render_html_template(self, email_params):
        """Teste le rendu du template HTML."""
        html_content = render_email_template(email_params, "email_template.html.j2")
        
        assert html_content is not None
        assert len(html_content) > 0
        # Les apostrophes sont échappées en HTML (L'IA devient L&#39;IA)
        assert ("L'IA révolutionne la médecine en 2025" in html_content 
                or "L&#39;IA révolutionne la médecine en 2025" in html_content)
        assert "https://domain.ntld" in html_content
        assert "50%" in html_content  # threshold formaté
        assert "ia" in html_content.lower()
        assert "agent" in html_content.lower()

    def test_render_text_template(self, email_params):
        """Teste le rendu du template texte."""
        text_content = render_email_template(email_params, "email_template.text.j2")
        
        assert text_content is not None
        assert len(text_content) > 0
        # Dans le template texte, les apostrophes peuvent être échappées ou non selon le template
        assert ("L'IA révolutionne" in text_content 
                or "L&#39;IA révolutionne" in text_content
                or "IA révolutionne" in text_content)
        assert "https://domain.ntld" in text_content
        assert "50%" in text_content

    def test_render_template_with_date(self, email_params):
        """Vérifie que la date est bien incluse dans le rendu."""
        html_content = render_email_template(email_params, "email_template.html.j2")
        
        # La date doit être au format dd/mm/yyyy
        current_date = datetime.now().strftime("%d/%m/%Y")
        assert current_date in html_content

    def test_render_template_with_empty_articles(self):
        """Teste le rendu avec une liste d'articles vide."""
        empty_params = EmailTemplateParams(
            articles=[],
            keywords=['test'],
            threshold=0.3
        )
        
        html_content = render_email_template(empty_params, "email_template.html.j2")
        assert html_content is not None
        # Le template devrait gérer gracieusement la liste vide


# =========================
# Tests de l'envoi d'email
# =========================

class TestEmailSending:
    """Tests de l'envoi d'emails."""

    @patch('app.send_articles_email.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Teste l'envoi réussi d'un email."""
        # Mock du serveur SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Appel de la fonction
        _send_email(
            subject="Test Subject",
            html_content="<html><body>Test HTML</body></html>",
            text_content="Test Text",
            sender="test@sender.com",
            to="test@recipient.com",
            smtp_server="smtp.test.com",
            smtp_port=587,
            login="testuser",
            password="testpass",
        )
        
        # Vérifications
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.ehlo.assert_called()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("testuser", "testpass")
        mock_server.sendmail.assert_called_once()
        
        # Vérifier les arguments de sendmail
        call_args = mock_server.sendmail.call_args[0]
        assert call_args[0] == "test@sender.com"
        assert call_args[1] == "test@recipient.com"
        assert "Test Subject" in call_args[2]

    @patch('app.send_articles_email.smtplib.SMTP')
    def test_send_email_contains_both_html_and_text(self, mock_smtp):
        """Vérifie que l'email contient bien les parties HTML et texte."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        _send_email(
            subject="Test",
            html_content="<p>HTML Content</p>",
            text_content="Text Content",
            sender="sender@test.com",
            to="recipient@test.com",
            smtp_server="smtp.test.com",
            smtp_port=587,
            login="user",
            password="pass",
        )
        
        # Récupérer le message envoyé
        sent_message = mock_server.sendmail.call_args[0][2]
        assert "text/plain" in sent_message
        assert "text/html" in sent_message
        assert "HTML Content" in sent_message
        assert "Text Content" in sent_message

    @patch('app.send_articles_email.smtplib.SMTP')
    def test_send_email_smtp_connection_error(self, mock_smtp):
        """Teste la gestion d'erreur de connexion SMTP."""
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Cannot connect")
        
        with pytest.raises(smtplib.SMTPConnectError):
            _send_email(
                subject="Test",
                html_content="<p>Test</p>",
                text_content="Test",
                sender="sender@test.com",
                to="recipient@test.com",
                smtp_server="invalid.smtp.com",
                smtp_port=587,
                login="user",
                password="pass",
            )

    @patch('app.send_articles_email.smtplib.SMTP')
    def test_send_email_authentication_error(self, mock_smtp):
        """Teste la gestion d'erreur d'authentification."""
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Invalid credentials")
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        with pytest.raises(smtplib.SMTPAuthenticationError):
            _send_email(
                subject="Test",
                html_content="<p>Test</p>",
                text_content="Test",
                sender="sender@test.com",
                to="recipient@test.com",
                smtp_server="smtp.test.com",
                smtp_port=587,
                login="baduser",
                password="badpass",
            )


# =========================
# Tests d'intégration
# =========================

class TestSendWatchArticlesIntegration:
    """Tests d'intégration de bout en bout."""

    @patch('app.send_articles_email.smtplib.SMTP')
    @patch('app.send_articles_email.render_email_template')
    def test_send_watch_articles_full_flow(self, mock_render, mock_smtp, email_params):
        """Teste le flux complet d'envoi d'articles de veille."""
        # Mock des rendus de template
        mock_render.side_effect = [
            "<html><body>Rendered HTML</body></html>",  # Premier appel (HTML)
            "Rendered Text Content"  # Deuxième appel (Text)
        ]
        
        # Mock du serveur SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Appel de la fonction principale
        send_watch_articles(email_params)
        
        # Vérifications du rendu
        assert mock_render.call_count == 2
        mock_render.assert_any_call(email_params, "email_template.html.j2")
        mock_render.assert_any_call(email_params, "email_template.text.j2")
        
        # Vérifications de l'envoi SMTP
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch('app.send_articles_email.smtplib.SMTP')
    def test_send_watch_articles_with_real_templates(self, mock_smtp, email_params):
        """Teste avec le rendu réel des templates (sans mock du rendu)."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Appel sans mocker le rendu
        send_watch_articles(email_params)
        
        # Vérifier que l'email a été envoyé
        mock_server.sendmail.assert_called_once()
        
        # Récupérer le contenu de l'email
        sent_message = mock_server.sendmail.call_args[0][2]
        
        # Vérifier que le contenu contient nos articles
        assert "L'IA révolutionne la médecine" in sent_message
        assert "énergie solaire" in sent_message
        assert "[VEILLE]" in sent_message

    @patch('app.send_articles_email.smtplib.SMTP')
    def test_send_watch_articles_subject_format(self, mock_smtp, email_params):
        """Vérifie le format du sujet de l'email."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        send_watch_articles(email_params)
        
        sent_message = mock_server.sendmail.call_args[0][2]
        
        # Vérifier le format du sujet
        assert "Subject: [VEILLE] Revue de veille techno du" in sent_message
        # La date devrait être au format dd/mm/yyyy HH:MM:SS
        current_date = datetime.now().strftime("%d/%m/%Y")
        assert current_date in sent_message


# =========================
# Tests de validation des données
# =========================

class TestEmailDataValidation:
    """Tests de validation des données d'entrée."""

    def test_email_params_with_missing_article_fields(self):
        """Teste le comportement avec des champs manquants dans les articles."""
        incomplete_articles = [
            {'title': 'Article sans lien', 'summary': 'Test'}
            # Manque: link, score, published, source
        ]
        
        params = EmailTemplateParams(
            articles=incomplete_articles,
            keywords=['test'],
            threshold=0.5
        )
        
        # Le rendu ne devrait pas planter
        try:
            html_content = render_email_template(params, "email_template.html.j2")
            assert html_content is not None
        except Exception as e:
            pytest.fail(f"Le rendu ne devrait pas échouer avec des champs manquants: {e}")

    def test_email_params_with_special_characters(self):
        """Teste le comportement avec des caractères spéciaux."""
        articles_with_special_chars = [
            {
                'title': "L'article avec des caractères spéciaux: é, à, ç, €, <>&",
                'link': 'https://domain.ntld',
                'summary': 'Résumé avec "guillemets" et \'apostrophes\'',
                'score': '75',
                'published': '2025-01-01T12:00:00',
                'source': 'rss'
            }
        ]
        
        params = EmailTemplateParams(
            articles=articles_with_special_chars,
            keywords=['test'],
            threshold=0.5
        )
        
        html_content = render_email_template(params, "email_template.html.j2")
        
        # Vérifier que l'autoescape fonctionne (< doit être échappé en &lt;)
        assert "&lt;" in html_content or "<" not in html_content.split("<body>")[1].split("</body>")[0]


# =========================
# Test de simulation manuel
# =========================

@pytest.mark.manual
@pytest.mark.skipif(True, reason="Test manuel - nécessite une vraie configuration SMTP")
def test_send_real_email_manual():
    """
    Test manuel pour envoyer un vrai email.
    
    À exécuter avec: pytest -m manual --no-skip
    Nécessite de configurer les vraies variables d'environnement SMTP.
    """
    articles = [
        {
            'title': "Test d'intégration - L'IA révolutionne la médecine en 2025",
            'link': 'https://domain.ntld',
            'summary': 'Ceci est un test d\'envoi d\'email depuis les tests d\'intégration',
            'score': '60',
            'published': '2025-01-01T20:30:00',
            'source': 'rss'
        },
    ]
    
    email_params = EmailTemplateParams(
        articles=articles,
        keywords=['test', 'intégration'],
        threshold=0.5
    )
    
    # Envoyer réellement l'email
    send_watch_articles(email_params)
    print("✅ Email de test envoyé avec succès!")
