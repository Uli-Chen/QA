import json
import os
import time
import argparse
import logging
import requests
import re

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

# 提示词模板
PROMPT_TEMPLATE = """你是一位专精于合成生物学和湿实验技术的科研顾问。请分析以下实验内容，并根据内容生成高质量的问题和答案。

## 实验内容:
```
{content}
```

## 来源:
{source}

## 任务:
1. 仔细分析上述实验内容，识别其中涉及的关键合成生物学概念、技术、方法或结果。
2. 从这些内容中，创建{num_qa_pairs}个有深度的问题，这些问题应该:
   - 基于实验内容中具体的科学原理或技术细节
   - 要求对合成生物学概念有深入理解
   - 考察实验设计、方法选择的合理性或局限性
   - 关联到更广泛的合成生物学应用场景或前沿研究
3. 对每个问题提供完整、准确的答案，答案应:
   - 直接基于实验内容，不添加未在内容中提及的事实
   - 应用合成生物学原理进行解释
   - 简洁但内容充实，通常在100-300字之间

## 回答要求:
对于每个问题，请提供:
1. 从原始内容中提取的与问题相关的简明摘录(content)
2. 问题本身(question)
3. 完整的答案(answer)
4. 原始来源(source)

## 输出格式:
你必须以JSON数组形式返回，每个问题-答案对作为一个对象:
[
  {{
    "content": "与问题相关的实验内容摘录...",
    "question": "基于内容的合成生物学问题",
    "answer": "详细的专业答案",
    "source": "{source}"
  }},
  ...
]

确保输出的是完全合法的JSON，不包含任何解释文本。只返回JSON数组，不要有其他文本。
"""

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
    
    # 构建提示词
    prompt = PROMPT_TEMPLATE.format(
        content=processed_content,
        source=source,
        num_qa_pairs=num_qa_pairs
    )
    
    try:
        # 调用API
        response = call_openai_api(api_key, prompt)
        
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

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='合成生物学QA生成器')
    parser.add_argument('--input_file', help='输入JSON文件路径')
    parser.add_argument('--output', default='./data/output.json', help='输出JSON文件路径')
    parser.add_argument('--api-key', help='API密钥')
    parser.add_argument('--qa-pairs', type=int, default=3, help='每条记录生成的问答对数量')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--start', type=int, default=0, help='起始索引')
    parser.add_argument('--count', type=int, default=None, help='处理记录数量')
    
    args = parser.parse_args()
    
    # 设置调试日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # 获取API密钥
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("未提供OpenAI API密钥，请使用--api-key参数或设置OPENAI_API_KEY环境变量")
        return
    
    # 加载数据
    data = load_data(args.input_file)
    
    # 选择数据子集
    end = args.start + args.count if args.count is not None else len(data)
    selected_data = data[args.start:end]
    logger.info(f"将处理 {len(selected_data)} 条记录 (从索引 {args.start} 开始)")
    
    # 顺序处理记录
    all_qa_pairs = []
    for i, record in enumerate(selected_data):
        logger.info(f"处理记录 {i+1}/{len(selected_data)}")
        qa_pairs = process_record(record, api_key, args.qa_pairs)
        all_qa_pairs.extend(qa_pairs)
        
        # 每处理一条记录保存一次结果，避免意外丢失
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(all_qa_pairs, f, ensure_ascii=False, indent=2)
        
        # 添加简短延迟，避免API速率限制
        if i < len(selected_data) - 1:
            time.sleep(2)
    
    logger.info(f"处理完成，共生成 {len(all_qa_pairs)} 个问答对")
    logger.info(f"结果已保存到: {args.output}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户中断程序执行")
    except Exception as e:
        logger.critical(f"程序执行失败: {str(e)}", exc_info=True)
