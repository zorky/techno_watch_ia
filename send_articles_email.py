from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja_filters import register_jinja_filters

from models.emails import EmailTemplateParams
from app.core.utils import get_environment_variable

# =========================
# Configuration SMTP
# =========================

SMTP_SERVER = get_environment_variable("SMTP_SERVER", "smtp.server.ntld")
SMTP_PORT = int(get_environment_variable("SMTP_PORT", "587"))
SMTP_LOGIN = get_environment_variable("SMTP_LOGIN", "jdoe")
SMTP_PASSWORD = get_environment_variable("SMTP_PASSWORD", "pwd")
SENDER = get_environment_variable("SENDER", "zorky00@gmail.com")
SEND_EMAIL_TO = get_environment_variable("SEND_EMAIL_TO", "jane.do@domain.ntld")

# =========================
# Rendu du template Jinja2
# =========================

def _set_env_render_filters():
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=True
    )
    register_jinja_filters(env)
    return env

def render_email_template(params: EmailTemplateParams, template_name: str, /) -> str:    
    env = _set_env_render_filters()
    template = env.get_template(template_name)
    threshold_str = f"{int(params.threshold * 100)}%"
    return template.render(articles=params.articles, 
                           keywords=params.keywords, 
                           threshold=threshold_str,
                           date=datetime.now().strftime("%d/%m/%Y"))

# =========================
# Envoi du mail
# =========================

def _send_email(
    subject: str,
    html_content: str,
    text_content: str,
    sender: str,
    to: str,
    smtp_server: str,
    smtp_port: int,
    login: str,
    password: str,
):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to

    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")

    msg.attach(part1)
    msg.attach(part2)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(login, password)
        server.sendmail(sender, to, msg.as_string())

def send_watch_articles(params: EmailTemplateParams):
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    email_subject = f"[VEILLE] Revue de veille techno du {current_date}"
    html_content = render_email_template(params, "email_template.html.j2")
    text_content = render_email_template(params, "email_template.text.j2")
    _send_email(
        subject=email_subject,
        html_content=html_content,
        text_content=text_content,
        sender=SENDER,
        to=SEND_EMAIL_TO,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
        login=SMTP_LOGIN,
        password=SMTP_PASSWORD,
    )

if __name__ == "__main__":
    from models.emails import EmailTemplateParams
    articles = [
        {'title': "L'IA révolutionne la médecine en 2025", 'link': 'https://domain.ntld', 'summary': 'résumé', 'score': '60 %'},
        {'title': "Comment l'énergie solaire transforme les villes", 'link': 'https://domain2.ntld', 'summary': 'résumé', 'score': '45 %'},
    # "Les dernières avancées en robotique industrielle",
    # "Comment l'énergie solaire transforme les villes",
    # "La cybersécurité face aux nouvelles menaces",
    # "Le cloud computing et la gestion des données",
    # "L'impact de la 5G sur les objets connectés",
    # "Les tendances du e-commerce en Europe",
    # "L'automatisation dans le secteur bancaire",
    # "L'évolution des véhicules électriques",
    # "L'intelligence artificielle dans l'éducation"
    ]
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    email_subject = f"[VEILLE] Revue de veille techno du {current_date}"
    email = EmailTemplateParams(
        articles=articles,
        keywords=['ia', 'agent'],
        threshold=0.5
    )
    html_content = render_email_template(email, "email_template.html.j2")
    text_content = render_email_template(email, "email_template.text.j2")
    print(html_content)
    print(text_content)
    _send_email(
        subject=email_subject,
        html_content=html_content,
        text_content=text_content,
        sender=SENDER,
        to=SEND_EMAIL_TO,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
        login=SMTP_LOGIN,
        password=SMTP_PASSWORD,
    )
