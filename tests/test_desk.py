import json
from pathlib import Path

from nlp_contract_amendment_map import desk_cli
from nlp_contract_amendment_map.renewal_cli import open_contracts
from nlp_contract_amendment_map.terms import ObligationDesk, SignedLibrary

ROOT = Path(__file__).parents[1] / 'fixtures'


def load_desk():
    materials = json.loads((ROOT / 'desk.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'desk_registry.json').read_text(encoding='utf-8'))
    library = SignedLibrary(registry['documents'], materials['clauses'])
    return ObligationDesk(library), materials


def load_ledger():
    materials = json.loads((ROOT / 'desk.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'desk_registry.json').read_text(encoding='utf-8'))
    ledger, sent = open_contracts(materials, registry)
    return ledger, {row['id']: row for row in sent}


def test_scoped_replacement_keeps_retained_exception():
    desk, _ = load_desk()
    answer = desk.effective(('MSA-1', '7'), '华东', '驻场', '2026-02-27', '2026-03-12')
    assert answer['status'] == 'ok'
    assert answer['days'] == 4
    assert [item['relation'] for item in answer['basis']] == ['替换', '保留']
    assert answer['exceptions'] == [{'clause': ['ATT-2', '9'], 'text': '交付期限遇公共假期顺延两日。', 'days': 2}]
    assert answer['limits'] == {'regions': ['华东'], 'services': ['驻场']}
    # 替换范围限定华东驻场，华北远程巡检仍按正文
    assert desk.effective(('MSA-1', '7'), '华北', '远程巡检', '2026-02-27', '2026-03-12')['days'] == 7


def test_reference_clause_inherits_deadline_from_old_version():
    desk, _ = load_desk()
    answer = desk.effective(('MSA-1', '7'), '华东', '远程巡检', '2026-02-27', '2026-03-12')
    assert answer['days'] == 5
    assert [item['relation'] for item in answer['basis']] == ['替换', '引用']
    assert answer['basis'][1]['clause'] == ['ATT-2', '5']


def test_same_work_date_supports_then_and_now_views():
    desk, _ = load_desk()
    then = desk.effective(('MSA-1', '7'), '华东', '驻场', '2026-02-27', '2026-03-01')
    now = desk.effective(('MSA-1', '7'), '华东', '驻场', '2026-02-27', '2026-03-12')
    # 补充协议 2 月 20 日生效但 3 月 12 日才归档，追溯缩短期限
    assert then['days'] == 7
    assert now['days'] == 4


def test_excluded_service_stays_on_base_clause():
    desk, _ = load_desk()
    answer = desk.effective(('MSA-1', '7'), '华北', '夜间驻场', '2026-02-27', '2026-05-13')
    assert answer['clause'] == ['MSA-1', '7']
    assert answer['days'] == 7


def test_ambiguous_reference_goes_back_for_review():
    desk, _ = load_desk()
    answer = desk.effective(('MSA-1', '7'), '华北', '驻场', '2026-02-27', '2026-05-13')
    assert answer['status'] == 'needs_review'
    assert answer['review']['reason'] == '被引条款存在多个候选'
    assert answer['review']['candidates'] == [['ATT-2', '9'], ['ATT-2B', '9']]


def test_reference_unambiguous_before_second_version_filed():
    desk, _ = load_desk()
    answer = desk.effective(('MSA-1', '7'), '华北', '驻场', '2026-02-27', '2026-02-15')
    assert answer['status'] == 'ok'
    assert answer['days'] == 5
    assert answer['exceptions'][0]['clause'] == ['ATT-2', '9']


def test_circular_exception_reference_goes_back_for_review():
    desk, _ = load_desk()
    answer = desk.effective(('ADD-2026-6', '10'), '华东', '驻场', '2026-04-10', '2026-04-09')
    assert answer['status'] == 'needs_review'
    assert answer['review']['reason'] == '例外条件互相引用，缺少可用起点'
    assert ['ADD-2026-6', '10'] in answer['review']['cycle']


def test_renumbered_reworded_clause_needs_no_notice():
    ledger, sent = load_ledger()
    result = ledger.compare(sent['MAIL-43'], '2026-04-02')
    assert result['current_answer']['clause'] == ['ADD-2026-5', '3']
    assert result['current_answer']['text'] != result['recorded_answer']['text']
    assert not result['needs_notice']
    assert result['disposal'] == '继续办理'


def test_real_deadline_change_locates_difference():
    ledger, sent = load_ledger()
    result = ledger.compare(sent['MAIL-41'], '2026-03-12')
    assert result['needs_notice']
    assert result['disposal'] == '补充说明'
    assert {'aspect': '期限', 'before': 7, 'after': 4} in result['differences']
    remote = ledger.compare(sent['MAIL-44'], '2026-03-12')
    assert remote['needs_notice']
    assert remote['differences'] == [{'aspect': '期限', 'before': 7, 'after': 5}]


def test_exception_change_locates_difference():
    ledger, sent = load_ledger()
    result = ledger.compare(sent['MAIL-45'], '2026-05-06')
    assert result['needs_notice']
    assert result['disposal'] == '补充说明'
    assert result['differences'] == [
        {'aspect': '例外', 'before': [{'days': 2}], 'after': [{'days': 3}]}
    ]


def test_ambiguity_hands_sent_answer_back_for_review():
    ledger, sent = load_ledger()
    result = ledger.compare(sent['MAIL-42'], '2026-05-13')
    assert result['needs_review']
    assert result['disposal'] == '交回核对'
    earlier = ledger.compare(sent['MAIL-42'], '2026-01-20')
    assert not earlier['needs_review']
    assert earlier['disposal'] == '继续办理'


def test_old_answer_text_and_basis_preserved():
    ledger, sent = load_ledger()
    result = ledger.compare(sent['MAIL-41'], '2026-03-12')
    assert result['recorded_answer'] == sent['MAIL-41']['answer']


def test_desk_cli_lists_then_and_now_materials(capsys):
    desk_cli.main([
        '华东', '驻场', '2026-02-27',
        '--known', '2026-03-12', '--then', '2026-03-01',
        '--materials', str(ROOT / 'desk.json'),
        '--registry', str(ROOT / 'desk_registry.json'),
    ])
    out = json.loads(capsys.readouterr().out)
    assert out['then']['answer']['days'] == 7
    assert out['current']['answer']['days'] == 4
    assert 'ADD-2026-3' not in out['then']['filed_documents']
    assert 'ADD-2026-3' in out['current']['filed_documents']
