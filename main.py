import os
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup

RSS_URL = "https://ascopubs.org/action/showFeed?jc=jco&type=etoc&feed=rss"
JOURNAL_NAME = "Journal of Clinical Oncology (JCO)"

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

HISTORY_FILE = "history.txt"

def get_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_to_history(url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def translate_text(text):
    if not text:
        return "无"
    try:
        clean_text = BeautifulSoup(text, "html.parser").get_text()
        translator = GoogleTranslator(source='en', target='zh-CN')
        return translator.translate(clean_text[:4500])
    except Exception as e:
        print(f"翻译失败: {e}")
        return "翻译失败，请查看原文。"

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

def main():
    print(f"开始检测 {JOURNAL_NAME} 最新文章...")
    feed = feedparser.parse(RSS_URL)
    history = get_history()
    new_articles = []

    for entry in feed.entries:
        link = entry.link
        if link in history:
            continue
        
        title_en = entry.title
        publish_time = entry.get('published', '未知时间')
        abstract_en = entry.get('description', '无摘要')
        
        print(f"发现新文章: {title_en}")
        title_zh = translate_text(title_en)
        abstract_zh = translate_text(abstract_en)
        
        article_html = f"""
        <div style="margin-bottom: 30px; border-bottom: 1px solid #ccc; padding-bottom: 20px;">
            <h2 style="color: #2c3e50;">{title_zh}</h2>
            <h3 style="color: #7f8c8d;">{title_en}</h3>
            <p><strong>期刊：</strong>{JOURNAL_NAME}</p>
            <p><strong>发表时间：</strong>{publish_time}</p>
            <p><strong>英文摘要：</strong><br>{abstract_en}</p>
            <p><strong>中文摘要：</strong><br>{abstract_zh}</p>
            <p><a href="{link}" style="background-color: #3498db; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">查看原文 (Click to Read)</a></p>
        </div>
        """
        new_articles.append({"html": article_html, "link": link})

    if new_articles:
        subject = f"【文献订阅】{JOURNAL_NAME} 更新了 {len(new_articles)} 篇新文章"
        body_content = "<h1>最新文献速递</h1>" + "".join([item["html"] for item in new_articles])
        send_email(subject, body_content)
        
        for item in new_articles:
            save_to_history(item["link"])
    else:
        print("没有发现新文章。")

if __name__ == "__main__":
    main()