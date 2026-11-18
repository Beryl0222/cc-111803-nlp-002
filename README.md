# 合同修订对义务引用的影响定位

本地文本工作区用于保存条款及引用解析相关的合成记录，并提供基础规范化和词项查看能力。

## 环境

需要 Python 3.11 或更新版本。运行程序仅使用 Python 标准库。测试依赖固定为 pytest 8.3.4，可执行 `python -m pip install -r requirements-dev.txt` 安装。

## 运行

用 `PYTHONPATH=src python -m nlp_contract_amendment_map.renewal_cli 2026-03-12` 核对续约解释。日期是经办人查看已归档签署材料的时点。签署文件用文号和条款号一起确定引用，归档日期与合同生效日期分别记录。样例已有按当时材料出具的书面解释。

从项目根目录执行 `PYTHONPATH=src python -m nlp_contract_amendment_map.cli ingest fixtures/records.json` 导入样例，随后执行 `PYTHONPATH=src python -m nlp_contract_amendment_map.cli list` 查看记录。工作数据写入 `var/records.json`。业务查询使用 fixtures/business.json 中的初始资料，约定见 fixtures/business-contract.md。执行 PYTHONPATH=src python -m nlp_contract_amendment_map.cli business 可查看当前业务目录结果。

样例为本地合成文本。记录包含来源、修订号和原文，当前工作区对空白做统一处理，并提供字符及英文词项切分。

## 测试

执行 `python -m pytest -q` 检查规范化、记录持久化和来源筛选。
