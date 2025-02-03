import glob
import re
import os
from collections import defaultdict
from bs4 import BeautifulSoup
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import inspect

def getargspec_compat(func):
    spec = inspect.getfullargspec(func)
    return (spec.args, spec.varargs, spec.varkw, spec.defaults)

inspect.getargspec = getargspec_compat
import pymorphy2
    
morph = pymorphy2.MorphAnalyzer()

def is_forwarded(text_div):
    parent = text_div.find_parent("div")
    while parent is not None:
        classes = parent.get("class", [])
        if "forwarded" in classes and "body" in classes:
            return True
        parent = parent.find_parent("div")
    return False

html_files = glob.glob("messages*.html")

messages_by_sender = defaultdict(list)

for file_path in html_files:
    with open(file_path, "r", encoding="utf-8") as file:
        html_content = file.read()
    soup = BeautifulSoup(html_content, "html.parser")
    
    message_blocks = soup.find_all("div", class_="message")
    if message_blocks:
        for block in message_blocks:
            sender_div = block.find("div", class_="from_name")
            text_div = block.find("div", class_="text")
            if sender_div and text_div:
                if is_forwarded(text_div):
                    continue
                sender = sender_div.get_text(strip=True)
                text = text_div.get_text(separator=" ", strip=True)
                messages_by_sender[sender].append(text)
    else:
        from_names = soup.find_all("div", class_="from_name")
        for sender_div in from_names:
            sender = sender_div.get_text(strip=True)
            text_div = sender_div.find_next_sibling("div", class_="text")
            if text_div:
                if is_forwarded(text_div):
                    continue
                text = text_div.get_text(separator=" ", strip=True)
                messages_by_sender[sender].append(text)

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

with open("stopwords.txt", "r", encoding="utf-8") as f:
    stopwords = {line.strip().lower() for line in f if line.strip()}

for sender, messages in messages_by_sender.items():
    aggregated_text = " ".join(messages)
    
    aggregated_text = re.sub(r'http[s]?://\S+', '', aggregated_text)
    aggregated_text = re.sub(r'www\.\S+', '', aggregated_text)
    
    pattern = r'\b(?:' + '|'.join(re.escape(word) for word in stopwords) + r')\b'
    aggregated_text = re.sub(pattern, '', aggregated_text, flags=re.IGNORECASE)
    aggregated_text = re.sub(r'\s+', ' ', aggregated_text).strip()
    
    tokens = re.findall(r'\w+', aggregated_text, flags=re.UNICODE)
    filtered_tokens = []
    for token in tokens:
        parse_results = morph.parse(token)
        if parse_results:
            pos = parse_results[0].tag.POS
            if pos in {"PREP", "CONJ", "PRCL"}:
                continue
        filtered_tokens.append(token)
    aggregated_text = " ".join(filtered_tokens)
    

    safe_sender = re.sub(r'[^\w\s-]', '', sender).strip().replace(" ", "_")
    
    dataset_filename = os.path.join(output_dir, f"dataset_{safe_sender}.txt")
    with open(dataset_filename, "w", encoding="utf-8") as f:
        f.write(aggregated_text)
    
    wc = WordCloud(width=2000, height=1000, background_color="white").generate(aggregated_text)
    
    plt.figure(figsize=(15, 7.5))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    
    wordcloud_filename = os.path.join(output_dir, f"wordcloud_{safe_sender}.png")
    plt.savefig(wordcloud_filename, dpi=300, bbox_inches='tight')
    plt.close()

print("Done")
