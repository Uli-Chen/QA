import json
import os
import time
import argparse
import logging
import requests
import re
import sys

CONFIG_FOLDER_PATH = '/home/user/project/25050300iGemLLM/QA/'
sys.path.append(CONFIG_FOLDER_PATH)
import path_config

from utils.singleton import S_Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("qa_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_api_headers(api_key):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

def load_data(input_file):
    """加载JSON数据文件"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"成功从{input_file}加载了{len(data)}条记录")
        return data
    except Exception as e:
        logger.error(f"加载数据失败: {str(e)}")
        raise

def preprocess_content(content, max_tokens=500000):
    """预处理内容，控制长度"""
    tokens = len(content) / 1.5

    if tokens > max_tokens:
        ratio = max_tokens / tokens
        content = content[:int(len(content) * ratio)]
        logger.warning(f"内容已截断至约{max_tokens}个token")
        content += "\n[内容已截断，仅显示部分实验内容]"

    return content

def call_openai_api(api_key, prompt, max_retries=3):
    headers = get_api_headers(api_key)
    api_url = "https://api.deepseek.com/v1/chat/completions"

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"调用API (尝试 {attempt+1}/{max_retries})")
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=120
            )

            if response.status_code != 200:
                logger.warning(f"API返回非200状态码: {response.status_code}")
                logger.warning(f"响应内容: {response.text}")

                if response.status_code == 429:  # 速率限制
                    wait_time = 10 + 5 * attempt
                    logger.warning(f"API速率限制，等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.warning(f"API调用失败: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    raise Exception("所有API调用尝试均失败")

def parse_json_response(response):
    """解析API返回的JSON响应"""
    logger.debug(f"API响应: {response}")

    # 尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("直接JSON解析失败，尝试提取JSON部分")

    # 查找可能的JSON开始和结束位置
    json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
    if json_match:
        json_text = json_match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            logger.error("提取的JSON无效")

    # 尝试修复常见JSON错误
    try:
        # 移除非JSON前缀和后缀
        cleaned_text = re.sub(r'^[^[]*', '', response)
        cleaned_text = re.sub(r'[^\]]*$', '', cleaned_text)

        # 确保布尔值和null是小写
        cleaned_text = cleaned_text.replace("True", "true").replace("False", "false").replace("None", "null")

        # 替换单引号为双引号
        cleaned_text = cleaned_text.replace("'", '"')

        return json.loads(cleaned_text)
    except Exception:
        logger.error("JSON修复失败，尝试使用正则表达式提取内容")

    # 使用正则表达式提取关键内容
    try:
        result = []
        contents = re.findall(r'"content"\s*:\s*"([^"]*)"', response)
        questions = re.findall(r'"question"\s*:\s*"([^"]*)"', response)
        answers = re.findall(r'"answer"\s*:\s*"([^"]*)"', response)
        sources = re.findall(r'"source"\s*:\s*"([^"]*)"', response)

        min_length = min(len(contents), len(questions), len(answers), len(sources))

        for i in range(min_length):
            result.append({
                "content": contents[i],
                "question": questions[i],
                "answer": answers[i],
                "source": sources[i]
            })

        if result:
            logger.info(f"通过正则表达式提取了{len(result)}个问答对")
            return result
    except Exception as e:
        logger.error(f"正则表达式提取失败: {str(e)}")

    logger.error("无法解析API响应")
    return []

def process_record(record, api_key, num_qa_pairs):
    """处理单条记录，生成问题和答案"""
    content = record.get("content", "")
    source = record.get("source", "未知来源")

    if not content or len(content) < 100:
        logger.warning(f"内容过短或为空，跳过: {source}")
        return []

    # 预处理内容
    processed_content = preprocess_content(content)
    # print('>>>>>> content', content)
    # print('>>>>>> processed_content', processed_content)

    # 构建提示词
    # print('>>>>>> S_Config().config["QAbyLLM"]["prompt"]')
    # print(S_Config().config['QAbyLLM']['prompt'])
    prompt = S_Config().config['QAbyLLM']['prompt'].format(
        content=processed_content,
        source=source,
        num_qa_pairs=num_qa_pairs
    )
    # print('>>>>>> prompt')
    # print(prompt)

    try:
        # 调用API
        response = call_openai_api(api_key, prompt)

        # print('>>>>>> response', response)
        # 解析响应
        qa_pairs = parse_json_response(response)

        # 确保source字段正确
        for qa in qa_pairs:
            qa["source"] = source

        logger.info(f"成功为来源 '{source}' 生成了 {len(qa_pairs)} 个问答对")
        return qa_pairs

    except Exception as e:
        logger.error(f"处理记录失败 ({source}): {str(e)}")
        return []

def main(config, expr_path):
    """主函数"""

    print('main')

    S_Config(config=config)
    QA_PAIRS = 3
    START = 0
    COUNT = None
    INPUT_CONTENT = path_config.PATH_MAIN + 'data/teams_wiki_data.json'
    OUTPUT_QA = expr_path + 'QAbyLLM.json'

    # parser = argparse.ArgumentParser(description='简化版合成生物学QA生成器')
    # parser.add_argument('--input_file', help='输入JSON文件路径')
    # parser.add_argument('--output', default='output.json', help='输出JSON文件路径')
    # parser.add_argument('--api-key', help='API密钥')
    # parser.add_argument('--qa-pairs', type=int, default=3, help='每条记录生成的问答对数量')
    # parser.add_argument('--debug', action='store_true', help='启用调试模式')
    # parser.add_argument('--start', type=int, default=0, help='起始索引')
    # parser.add_argument('--count', type=int, default=None, help='处理记录数量')
    # args = parser.parse_args()

    # 设置调试日志级别
    # if args.debug:
    #     logger.setLevel(logging.DEBUG)

    # 获取API密钥
    # api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    # if not api_key:
    #     logger.error("未提供OpenAI API密钥，请使用--api-key参数或设置OPENAI_API_KEY环境变量")
    #     return
    # print(api_key)

    # 加载数据
    # data = load_data(args.input_file)
    data = load_data(INPUT_CONTENT)

    # 选择数据子集
    end = START + COUNT if COUNT is not None else len(data)
    selected_data = data[START:end]
    logger.info(f"将处理 {len(selected_data)} 条记录 (从索引 {START} 开始)")

    # 顺序处理记录
    all_qa_pairs = []
    for i, record in enumerate(selected_data):
        logger.info(f"处理记录 {i+1}/{len(selected_data)}")
        qa_pairs = process_record(record, S_Config().config['QAbyLLM']['apiKey'], QA_PAIRS)
        all_qa_pairs.extend(qa_pairs)

        # 每处理一条记录保存一次结果，避免意外丢失
        with open(OUTPUT_QA, 'w', encoding='utf-8') as f:
            json.dump(all_qa_pairs, f, ensure_ascii=False, indent=2)

        # 添加简短延迟，避免API速率限制
        if i < len(selected_data) - 1:
            time.sleep(2)

    logger.info(f"处理完成，共生成 {len(all_qa_pairs)} 个问答对")
    logger.info(f"结果已保存到: {OUTPUT_QA}")
