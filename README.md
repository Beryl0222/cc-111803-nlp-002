# 合同修订对义务引用的影响定位

本地文本工作区用于保存条款及引用解析相关的合成记录，并提供基础规范化和词项查看能力。

## 环境

需要 Python 3.11 或更新版本。运行程序仅使用 Python 标准库。测试依赖固定为 pytest 8.3.4，可执行 `python -m pip install -r requirements-dev.txt` 安装。

## 运行

用 `PYTHONPATH=src python -m nlp_contract_amendment_map.renewal_cli 2026-03-12` 核对续约解释。日期是经办人查看已归档签署材料的时点。签署文件用文号和条款号一起确定引用，归档日期与合同生效日期分别记录。样例已有按当时材料出具的书面解释。

用 `PYTHONPATH=src python -m nlp_contract_amendment_map.desk_cli 华东 驻场 2026-02-27 --known 2026-03-12 --then 2026-03-01` 查询义务适用。经办人选定服务地区、服务类型和履约日，结果给出适用条款、期限、保留的例外和追到签署文本的依据链。`--known` 是今天查看材料的时点，`--then` 可对照历史时点；同一履约日下两个时点能采用的签署材料分别列出。

用 `PYTHONPATH=src python -m nlp_contract_amendment_map.renewal_cli 2026-05-13 --materials fixtures/desk.json --registry fixtures/desk_registry.json` 复核 desk 样例的已发解释。

从项目根目录执行 `PYTHONPATH=src python -m nlp_contract_amendment_map.cli ingest fixtures/records.json` 导入样例，随后执行 `PYTHONPATH=src python -m nlp_contract_amendment_map.cli list` 查看记录。工作数据写入 `var/records.json`。业务查询使用 fixtures/business.json 中的初始资料，约定见 fixtures/business-contract.md。执行 PYTHONPATH=src python -m nlp_contract_amendment_map.cli business 可查看当前业务目录结果。

## 条款关系模型

签署材料把替换范围（replaces）、保留的例外（retains）、引用（refers）、限定（regions/services）、排除（excludes）和生效时间（effective）分开记录，补充协议不整段代替正文。归档日期（filed）决定经办人当时能看到哪些材料，与义务生效日分开使用。同一编号可被几版附件重复使用，条款以文号加条款号定位；只写条款号的引用按当时已归档的材料收集候选。

查询结果带 status：`ok` 表示可直接采用；`needs_review` 表示被引条款存在多个候选，或例外条件互相引用却没有可用起点，受影响的解释交回核对，review 字段给出候选或循环路径。

复核已发解释时按经办人实际承担的义务（期限和保留的例外）比较：新确认的条款改了编号或换了说法不触发重发；某个范围内的期限或例外真变时，differences 定位实质差异。disposal 给出处理方向：继续办理、补充说明或交回核对。旧答复的当时文字和依据原样保留在 recorded_answer 中。

样例为本地合成文本。记录包含来源、修订号和原文，当前工作区对空白做统一处理，并提供字符及英文词项切分。

## 测试

执行 `python -m pytest -q` 检查规范化、记录持久化、来源筛选、条款关系解析、交回核对和已发解释复核。
