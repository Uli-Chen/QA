import csv
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import os
import json
import logging
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
# from requests.packages.urllib3.util.retry import Retry
from urllib3.util import Retry
from fake_useragent import UserAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='wiki_crawler.log'
)
logger = logging.getLogger(__name__)

# 配置请求会话
def get_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # 使用fake_useragent库生成随机UA
    try:
        ua = UserAgent()
        user_agent = ua.random
    except:
        # 备用User-Agent列表
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        ]
        user_agent = random.choice(user_agents)

    # 构建更完善的请求头
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',  # Do Not Track
        'Referer': 'https://www.google.com/'  # 伪装来源
    }
    session.headers.update(headers)
    return session

# 读取CSV文件
def read_team_data(csv_file):
    try:
        df = pd.read_csv(csv_file)
        logger.info(f"成功读取CSV文件，共有 {len(df)} 条队伍数据")
        return df
    except Exception as e:
        logger.error(f"读取CSV文件失败: {str(e)}")
        return None

# 生成可能的实验/协议页面URL
def generate_possible_urls(wiki_url):

    base_url = wiki_url.rstrip('/')

    experiment_paths = [
        '/experiment', '/experiments', '/Experiment', '/Experiments',
        '/wetlab', '/wet-lab', '/WetLab', '/Wet_Lab',
    ]

    protocol_paths = [
        '/protocol', '/protocols', '/Protocol', '/Protocols',
    ]

    result_paths = [
        '/results','/result','/Results','/Result','/engineering','/Engineering'
    ]

    possible_urls = []
    for path in experiment_paths+protocol_paths:
        possible_urls.append(base_url + path)

    return possible_urls

# 检测页面是否存在
def check_page_exists(url, session):
    try:
        response = session.head(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

# 获取页面内容
def fetch_page(url, session):
    try:
        logger.info(f"正在获取页面: {url}")
        response = session.get(url, timeout=15)
        response.raise_for_status()
        time.sleep(random.uniform(1, 3))  # 随机延迟，避免请求过快
        return response.text
    except Exception as e:
        logger.error(f"获取页面 {url} 失败: {str(e)}")
        return None

# 提取导航链接
def extract_nav_links(soup, base_url):
    nav_links = {}

    # 尝试各种可能的导航元素
    nav_elements = [
        soup.find('nav'),
        soup.find(class_=re.compile(r'nav|navigation|menu|sidebar', re.I)),
        soup.find(id=re.compile(r'nav|navigation|menu|sidebar', re.I)),
    ]

    for nav in nav_elements:
        if nav:
            links = nav.find_all('a')
            for link in links:
                href = link.get('href')
                text = link.get_text().strip().lower()

                if href and not href.startswith(('#', 'javascript:')):
                    full_url = urljoin(base_url, href)

                    # 寻找与实验或协议相关的关键词
                    exp_keywords = ['experiment', 'lab', 'wetlab', 'wet lab']
                    protocol_keywords = ['protocol', 'method', 'procedure']

                    for keyword in exp_keywords:
                        if keyword in text:
                            nav_links['experiment'] = full_url
                            break

                    for keyword in protocol_keywords:
                        if keyword in text:
                            nav_links['protocol'] = full_url
                            break

    return nav_links

# 清理HTML内容，提取纯文本
def clean_html_content(html_content):
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')

    # 移除script和style元素
    for script in soup(["script", "style"]):
        script.extract()

    # 获取文本
    text = soup.get_text(separator="\n")

    # 清理多余的空白和空行
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    clean_text = '\n'.join(lines)

    return clean_text

# 提取实验内容
def extract_experiment_content(soup, page_url):
    content_sections = {}

    # 尝试不同的内容定位策略
    # 策略1: 通过标题定位
    headings = soup.find_all(['h1', 'h2', 'h3'], string=re.compile(r'experiment|lab|protocol|method|procedure', re.I))
    for heading in headings:
        section_title = heading.get_text().strip()
        section_content = []

        # 收集该标题后的内容直到下一个同级标题
        current_element = heading.next_sibling
        while current_element:
            if current_element.name == heading.name:
                break
            if current_element.name in ['p', 'div', 'ul', 'ol', 'table', 'pre', 'code']:
                section_content.append(str(current_element))
            current_element = current_element.next_sibling

        if section_content:
            content_sections[section_title] = ''.join(section_content)

    # 策略2: 通过特定ID或类定位
    content_elements = soup.find_all(id=re.compile(r'experiment|lab|protocol|method|procedure', re.I))
    content_elements += soup.find_all(class_=re.compile(r'experiment|lab|protocol|method|procedure', re.I))

    for elem in content_elements:
        key = elem.get('id', '') or elem.get('class', [''])[0]
        content_sections[key] = str(elem)

    # 策略3: 如果没有找到任何特定内容，提取整个页面主要内容区域
    if not content_sections:
        main_content = soup.find('main') or soup.find(id='content') or soup.find(class_='content')
        if main_content:
            content_sections['main_content'] = str(main_content)
        else:
            # 最后的策略: 提取<body>下所有<p>和<div>元素
            body_content = [str(p) for p in soup.find_all(['p', 'div'], recursive=False)]
            if body_content:
                content_sections['body_content'] = ''.join(body_content)

    # 如果所有策略都失败，提取整个页面
    if not content_sections:
        content_sections['full_page'] = str(soup.body)

    # 整合所有内容部分, 转换为纯文本
    combined_content = ""
    for section_name, section_html in content_sections.items():
        clean_text = clean_html_content(section_html)
        if clean_text:
            combined_content += f"=== {section_name} ===\n{clean_text}\n\n"

    return combined_content.strip()

# 爬取队伍Wiki并创建JSON格式记录
def crawl_team_wiki(team_row, results):
    team_id = team_row['id']
    team_name = team_row['team']
    wiki_url = team_row['wiki']
    print(team_id)

    logger.info(f"开始处理队伍 {team_name} (ID: {team_id})")

    session = get_session()

    # 获取主维基页面
    main_page_html = fetch_page(wiki_url, session)
    if not main_page_html:
        logger.warning(f"无法获取队伍 {team_name} 的主Wiki页面")
        return

    main_soup = BeautifulSoup(main_page_html, 'html.parser')

    # 1. 尝试从导航中找到实验或协议页面
    nav_links = extract_nav_links(main_soup, wiki_url)

    # 2. 生成可能的实验/协议页面URL
    possible_urls = generate_possible_urls(wiki_url)

    # 合并导航链接和可能的URL
    if 'experiment' in nav_links:
        possible_urls.insert(0, nav_links['experiment'])
    if 'protocol' in nav_links:
        possible_urls.insert(0, nav_links['protocol'])

    # 去重
    possible_urls = list(set(possible_urls))

    # 查找有效页面并提取内容
    all_content = ""
    found_pages = []

    for url in possible_urls:
        if check_page_exists(url, session):
            page_html = fetch_page(url, session)
            if page_html:
                soup = BeautifulSoup(page_html, 'html.parser')
                page_content = extract_experiment_content(soup, url)
                if page_content:
                    all_content += f"【页面: {url}】\n{page_content}\n\n"
                    found_pages.append(url)

    # 如果没有找到特定页面，尝试从主页提取
    if not found_pages:
        logger.info(f"未找到队伍 {team_name} 的专门实验/协议页面，尝试从主页提取相关内容")
        main_page_content = extract_experiment_content(main_soup, wiki_url)
        if main_page_content:
            all_content += f"【页面: {wiki_url}】\n{main_page_content}\n\n"
            found_pages.append(wiki_url)

    # 只有在找到内容的情况下才添加到结果
    if all_content:
        # 创建JSON格式的记录
        record = {
            "content": all_content.strip(),
            "question": "",
            "answer": "",
            "source": f"{team_name} - {wiki_url}"
        }

        # 添加队伍ID作为元数据
        record["_meta"] = {
            "team_id": team_id,
            "found_pages": found_pages
        }

        results.append(record)
        logger.info(f"完成队伍 {team_name} 的数据抓取，找到 {len(found_pages)} 个相关页面")
    else:
        logger.warning(f"no available data for {team_name} team")

# 保存结果为JSON格式
def save_results(results, output_file):
    # 移除结果中的元数据，创建最终输出格式
    final_results = []
    for record in results:

        #简单的过滤垃圾信息
        if(len(record["content"])<5000):
            continue

        clean_record = {
            "content": record["content"],
            "question": record["question"],
            "answer": record["answer"],
            "source": record["source"]
        }
        final_results.append(clean_record)

    # 保存JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)

    logger.info(f"saved to: {output_file}")

    # 创建带元数据的版本（用于分析）
    meta_output_file = output_file.replace('.json', '_with_meta.json')
    with open(meta_output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 创建摘要CSV
    summary_data = []
    for record in results:
        summary_data.append({
            'team_id': record['_meta']['team_id'],
            'team_name': record['source'].split(' - ')[0],
            'wiki_url': record['source'].split(' - ')[1],
            'found_pages': ', '.join(record['_meta']['found_pages']),
            'content_length': len(record['content'])
        })

    summary_df = pd.DataFrame(summary_data)
    summary_csv = output_file.replace('.json', '_summary.csv')
    summary_df.to_csv(summary_csv, index=False)

    logger.info(f"summary saved to: {summary_csv}")
    logger.info(f"data of {len(results)} teams have been obtained, total length: {sum(len(r['content']) for r in results)} chars")

# 主函数
def main(csv_file, output_file='teams_wiki_data.json', max_workers=5):
    logger.info("start crawling")

    # 读取CSV数据
    df = read_team_data(csv_file)
    if df is None:
        return

    # 存储结果
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for _, row in df.iterrows():
            executor.submit(crawl_team_wiki, row, results)

    # 保存结果
    save_results(results, output_file)

    logger.info(f" {len(df)} teams in total，data of {len(results)} team obtained")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='wiki_crawler')
    parser.add_argument('--csv_file', default='./data/teams_cleaned.csv',help='team wiki csv filepath')
    parser.add_argument('--output', default='./data/teams_wiki_data.json', help='output in json')
    parser.add_argument('--workers', type=int, default=5, help='workers number')

    args = parser.parse_args()

    main(args.csv_file, args.output, args.workers)
