# from jinja2 import Environment, FileSystemLoader
# from datetime import datetime
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText

# def render_email_template(articles: list[dict], template_name: str) -> str:
#     env = Environment(loader=FileSystemLoader('templates'))
#     template = env.get_template(template_name)
#     return template.render(
#         articles=articles,
#         date=datetime.now().strftime('%d/%m/%Y')
#     )

# # Exemple d'utilisation
# articles = [
#     {
#         "title": "Nouveautés en IA générative",
#         "source": "NYT Technology",
#         "link": "https://example.com/article1",
#         "summary": "Résumé généré par l'IA...",
#         "keywords": ["IA", "générative"]
#     },
#     # ... autres articles
# ]

# def send_email(subject: str, html_content: str, text_content: str, to: str, smtp_server: str, smtp_port: int, login: str, password: str):
#     msg = MIMEMultipart('alternative')
#     msg['Subject'] = subject
#     msg['From'] = login
#     msg['To'] = to

#     part1 = MIMEText(text_content, 'plain')
#     part2 = MIMEText(html_content, 'html')

#     msg.attach(part1)
#     msg.attach(part2)

#     with smtplib.SMTP(smtp_server, smtp_port) as server:
#         server.starttls()
#         server.login(login, password)
#         server.sendmail(login, to, msg.as_string())

# # Exemple d'utilisation
# # send_email(
# #     subject="Veille Techno - Résumé du jour",
# #     html_content=html_content,
# #     text_content=text_content,
# #     to="olivier.duval@example.com",
# #     smtp_server="smtp.example.com",
# #     smtp_port=587,
# #     login="ton_email@example.com",
# #     password="ton_mot_de_passe"
# # )

# if __name__ == "__main__":    
#     html_content = render_email_template(articles, 'email_template.html.j2')
#     text_content = render_email_template(articles, 'email_template.txt.j2')
