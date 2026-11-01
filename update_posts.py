import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import re

RSS_URL = "https://rss.blog.naver.com/run_daramg.xml"
HTML_FILE = "index.html"

def insert_into_category(html, category, li_html):
    # data-category="카테고리명" 섹션의 <ul class="post-list"> 바로 아래에 새 글 삽입
    pattern = rf'(<section class="category-section" data-category="{re.escape(category)}"[^>]*>.*?<ul[^>]*class="post-list"[^>]*>)'
    match = re.search(pattern, html, flags=re.DOTALL)
    if match:
        insert_pos = match.end()
        return html[:insert_pos] + "\n" + li_html + html[insert_pos:], True
    return html, False

def update_counts(html):
    total_posts = 0
    # 각 카테고리 섹션별 실제 <li> 개수를 세어 배지 및 좌측 탭 숫자 자동 갱신
    sec_pattern = r'(<section class="category-section" data-category="([^"]+)"[^>]*>)(.*?)(</section>)'
    
    def sec_replacer(match):
        nonlocal total_posts
        header, cat, body, footer = match.groups()
        if cat == "새글":
            return match.group(0)
        count = len(re.findall(r'<li>\s*<a ', body))
        total_posts += count
        new_body = re.sub(r'(<span class="section-badge">)\d+(개의 글</span>)', rf'\g<1>{count}\g<2>', body)
        return header + new_body + footer

    html = re.sub(sec_pattern, sec_replacer, html, flags=re.DOTALL)

    # 좌측 사이드바 카테고리별 숫자 업데이트
    for sec_match in re.finditer(sec_pattern, html, flags=re.DOTALL):
        cat = sec_match.group(2)
        if cat == "새글":
            continue
        count = len(re.findall(r'<li>\s*<a ', sec_match.group(3)))
        btn_pattern = rf'(onclick="filterCategory\(\'{re.escape(cat)}\', this\)"[^>]*>.*?<span class="cat-count">)\d+(</span>)'
        html = re.sub(btn_pattern, rf'\g<1>{count}\g<2>', html, flags=re.DOTALL)

    # 전체보기 숫자 업데이트
    html = re.sub(r'(<span class="cat-count" id="count-all">)\d+(</span>)', rf'\g<1>{total_posts}\g<2>', html)
    return html

def main():
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()

    items = root.findall("./channel/item")
    added_count = 0

    # 최신 글이 맨 위에 오도록 역순(오래된 순 -> 최신 순)으로 검사 및 삽입
    for item in reversed(items):
        title = item.find("title").text or ""
        link = item.find("link").text or ""
        category_el = item.find("category")
        category = category_el.text.strip() if (category_el is not None and category_el.text) else "기타"
        pub_date = item.find("pubDate").text or ""

        # 글 번호 추출
        match = re.search(r'run_daramg/(\d+)', link)
        if not match:
            continue
        log_no = match.group(1)

        # 이미 index.html에 있는 글 번호면 건너뛰기
        if log_no in html_content:
            continue

        # 날짜 포맷 변환 (YYYY.MM.DD.)
        try:
            dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            date_str = dt.strftime("%Y.%m.%d.")
        except Exception:
            date_str = datetime.now().strftime("%Y.%m.%d.")

        mobile_url = f"https://m.blog.naver.com/run_daramg/{log_no}"
        safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        li_html = f'          <li><a href="{mobile_url}">{safe_title}</a><span class="date">{date_str}</span></li>'

        # 1순위: 일치하는 카테고리 섹션에 삽입
        html_content, success = insert_into_category(html_content, category, li_html)
        
        # 2순위: 만약 네이버에 새 카테고리를 만들어서 기존 6개와 이름이 다르면 상단 '새글' 섹션에 삽입
        if not success:
            marker = "<!-- AUTO-POST-LIST -->"
            if marker in html_content:
                html_content = html_content.replace(marker, marker + "\n" + li_html, 1)
                success = True

        if success:
            added_count += 1
            print(f"[추가 완료] [{category}] {title} ({log_no})")

    if added_count > 0:
        html_content = update_counts(html_content)
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"총 {added_count}개의 새 글이 카테고리별로 반영되었습니다.")
    else:
        print("새로 추가할 블로그 글이 없습니다.")

if __name__ == "__main__":
    main()
