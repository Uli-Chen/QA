'''
batch0
'''

import sys
import os
import json
import subprocess

CONFIG_FOLDER_PATH = '/home/user/project/25050300iGemLLM/QA/'
sys.path.append(CONFIG_FOLDER_PATH)
import path_config

def batch_run(batch_folder):
    print(f"batch_run(batch_folder=\"{batch_folder})\"")

    cnt_run = 1

    prompt_options = [
"""
你是一位专精于合成生物学和湿实验技术的科研顾问。请分析以下实验内容，并根据内容生成高质量的问题和答案。

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
   - 简洁但内容充实，通常在50-100词之间
   - 不能要求过于具体难以简单验证的定量回答，使用定性回答
3. 对每个问题提供完整、准确的答案，答案应:
   - 直接基于实验内容，不添加未在内容中提及的事实
   - 应用合成生物学原理进行解释
   - 简洁但内容充实，通常在50-100字之间
   - 不要进行过于具体难以简单验证的定量回答，使用定性回答

## 回答要求:
对于每个问题，请提供:
1. 从原始内容中提取的与问题相关的简明摘录(content)
2. 问题本身(question)
3. 完整的答案(answer)
4. 原始来源(source)

## 输出格式:
你必须以JSON数组形式返回，每个问题-答案对作为一个对象，全部使用英文:
[
  {{
    "content": "与问题相关的实验内容摘录...",
    "question": "基于内容的合成生物学问题",
    "answer": "详细的专业答案",
    "source": "{source}"
  }},
  ...
]

确保输出的是完全合法的JSON，不包含任何解释文本。只返回JSON数组，不要有其他文本，全部使用英文。
"""
,
"""
你是一位专精于合成生物学和湿实验技术的科研顾问。请分析以下实验内容，并根据内容生成高质量的问题和答案。

## 实验内容:
```
{content}
```

## 来源:
{source}

## 任务:
1. 仔细分析上述实验内容，识别其中涉及的关键合成生物学概念、技术、方法或结果。
2. 从这些内容中，创建{num_qa_pairs}个有深度的选择题，每个选择题的题干包括一段题干和A,B,C 3个选项：
    a) 题干的要求
        - 基于实验内容中具体的科学原理或技术细节
        - 要求对合成生物学概念有深入理解
        - 考察实验设计、方法选择的合理性或局限性
        - 关联到更广泛的合成生物学应用场景或前沿研究
        - 简洁但内容充实，通常在50-100词之间
        - 不能要求过于具体难以简单验证的定量回答，使用定性回答
    b) 每个选项的要求
        - 三个选项中有且只有一个完全正确，其余两个选项是错误的
        - 选项中的错误不能过于隐晦，也不能过于明显，每个选项应该让粗读过整个“实验内容”的生物学专业学生在30秒左右大致判断出正误
        - 三个选项应该围绕题干，考察合成生物学相关知识，且选项之间有一定的关联
        - 完整、准确，直接基于实验内容，不添加未在内容中提及的事实
        - 简洁但内容充实，通常在30-60词之间
        - 不要涉及过于具体难以简单验证的定量内容
3. 对于每道选择题，提供正确选项的序号(A,B,C)以及一段解释，解释应:
    - 首先针对每个选项分别进行解释，然后对选项之间进行比较形式的解释
    - 直接基于实验内容，不添加未在内容中提及的事实
    - 应用合成生物学原理进行解释
    - 简洁但内容充实，通常在50-100词之间

## 回答要求:
对于每个问题，请提供:
1. 从原始内容中提取的与问题相关的简明摘录(content)
2. 问题(question)
    a) 题干
    b) 选项A,B,C
3. 正确的选项和解释(answer)
    a) 正确选项的序号(A,B,C)
    b) 解释
4. 原始来源(source)

## 输出格式:
你必须以JSON数组形式返回，每个问题-答案对作为一个对象，全部使用英文:
[
  {{
    "content": "与问题相关的实验内容摘录...",
    "question": {{
        "stem": "基于内容的合成生物学选择题的题干",
        "options": {{
            "A": "选项A",
            "B": "选项B",
            "C": "选项C"
        }}
    }},
    "answer": {{
        "correct_option": "一个字符A,B或C",
        "explanation": "详细的专业解释"
    }},
    "source": "{source}"
  }},
  ...
]

确保输出的是完全合法的JSON，不包含任何解释文本。只返回JSON数组，不要有其他文本，全部使用英文。
"""
,
"""
你是一位专精于合成生物学和湿实验技术的科研顾问。请分析以下实验内容，并根据内容生成高质量的问题和答案。

## 实验内容:
```
{content}
```

## 来源:
{source}

## 任务:
1. 仔细分析上述实验内容，识别其中涉及的关键合成生物学概念、技术、方法或结果。
2. 从这些内容中，创建{num_qa_pairs}个有深度的选择题，每个选择题的题干包括一段题干和A,B,C 3个选项：
    a) 题干的要求
        - 基于实验内容中具体的科学原理或技术细节
        - 要求对合成生物学概念有深入理解
        - 考察实验设计、方法选择的合理性或局限性
        - 关联到更广泛的合成生物学应用场景或前沿研究
        - 简洁但内容充实，通常在50-100词之间
        - 不能要求过于具体难以简单验证的定量回答，使用定性回答
        - 挑选原始内容中讲的比较细致，适合出成题的内容
        - 涉及到的所有内容、知识点和数据都必须在原文中明确提出，不能是自行编造或根据外部知识
    b) 每个选项的要求
        - 三个选项中有且只有一个完全正确，其余两个选项是错误的
        - 选项中的错误不能过于隐晦，也不能过于明显，每个选项应该让粗读过整个“实验内容”的生物学专业学生在30秒左右大致判断出正误
        - 三个选项应该围绕题干，考察合成生物学相关知识，且选项之间有一定的关联
        - 完整、准确，直接基于实验内容，不添加未在内容中提及的事实
        - 简洁但内容充实，通常在30-60词之间
        - 不要涉及过于具体难以简单验证的定量内容
        - 判断正误所用的所有内容、知识点和数据都必须在原文中能够找到，不能是自行编造或根据外部知识
3. 对于每道选择题，提供正确选项的序号(A,B,C)以及一段解释，解释应:
    - 首先针对每个选项分别进行解释，然后对选项之间进行比较形式的解释
    - 直接基于实验内容，不添加未在内容中提及的事实
    - 应用合成生物学原理进行解释
    - 简洁但内容充实，通常在50-100词之间
    - 涉及到的所有内容、知识点和数据都必须在原文中明确提出，不能是自行编造或根据外部知识

## 回答要求:
对于每个问题，请提供:
1. 从原始内容中提取的与问题相关的简明摘录(content)
2. 问题(question)
    a) 题干
    b) 选项A,B,C
3. 正确的选项和解释(answer)
    a) 正确选项的序号(A,B,C)
    b) 解释
4. 原始来源(source)

## 输出格式:
你必须以JSON数组形式返回，每个问题-答案对作为一个对象，全部使用英文:
[
  {{
    "content": "与问题相关的实验内容摘录...",
    "question": {{
        "stem": "基于内容的合成生物学选择题的题干",
        "options": {{
            "A": "选项A",
            "B": "选项B",
            "C": "选项C"
        }}
    }},
    "answer": {{
        "correct_option": "一个字符A,B或C",
        "explanation": "详细的专业解释"
    }},
    "source": "{source}"
  }},
  ...
]

确保输出的是完全合法的JSON，不包含任何解释文本。只返回JSON数组，不要有其他文本，全部使用英文。
"""
    ]

    with open(path_config.PATH_EXPERIMENT_MANAGER + "default_config.json", 'r') as f:
        default_config = json.load(f)

    for run_idx in range(cnt_run):
        for idx0, prompt in enumerate(prompt_options):
            if idx0 != 2:
                continue

            lFN = f"_{idx0}/" ############
            if cnt_run != 1:
                lFN = f"_r{run_idx}" + lFN
            lFN = "run" + lFN
            one_run_folder = os.path.join(batch_folder, lFN)
            if not os.path.exists(one_run_folder):
                os.makedirs(one_run_folder)
            new_config_path = os.path.join(one_run_folder, 'config.json')
            new_config = default_config.copy()

            ###
            new_config['entry'] = 'QAbyLLM.py'
            new_config['QAbyLLM']['apiKey'] = 'sk-de73abf927ca4e1d9b7d310be834f3ec'
            ###
            new_config['QAbyLLM']['prompt'] = prompt
            ###

            with open(new_config_path, 'w') as f:
                json.dump(new_config, f, indent=4)

            subprocess.run(["python", path_config.PATH_EXPERIMENT_MANAGER + "run.py", new_config_path])
            print(lFN + "completed")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python batchXX.py <batchFolderRelativePath>")
        sys.exit(1)

    batch_folder = path_config.PATH_EXPERIMENTS + sys.argv[1]
    batch_run(batch_folder)
