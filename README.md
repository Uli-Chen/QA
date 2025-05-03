# iGEM Wiki Crawler & QA Generation via LLM

This repository provides a set of scripts for **automatically crawling iGEM team wiki pages**, filtering teams based on custom criteria, and generating **question-answer (QA) pairs** using **large language models (LLMs)**. It is designed to facilitate **automated knowledge extraction** and **QA dataset construction** in the context of synthetic biology.

---

## Repository Overview

### `wiki_crawler.py`
**Function:**  
Scrapes iGEM team wiki pages and extracts relevant wetlab content (currently sections like **"Experiment"** and **"Proposal"**) for downstream analysis or QA generation.

---

### `team_filter.py`
**Function:**  
Filters iGEM teams based on specific criteria such as **year**, helping narrow down relevant entries for crawling or QA.

---

### `QAbyLLM.py`
**Function:**  
Generates **question-answer pairs** from the crawled wiki data using an LLM.

**Usage:**
```bash
python QAbyLLM.py \
  --input_file "path/to/teams_wiki_data.json" \
  --output "path/to/output_QA.json" \
  --api-key "your_openai_or_other_llm_api_key" \
  --qa-pairs 5
```

---

## TODO

- [ ] Integrate other LLMs to perform **cross-validation** of generated QA pairs.
- [ ] Perform **prompt engineering and optimization** to improve the relevance, accuracy, and diversity of QA generation results.
