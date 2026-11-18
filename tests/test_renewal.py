import json
from pathlib import Path

from nlp_contract_amendment_map.renewal_cli import open_contracts


def test_backdated_clause_changes_only_applicable_current_reply():
    root = Path(__file__).parents[1] / 'fixtures'
    materials = json.loads((root / 'renewal.json').read_text())
    registry = json.loads((root / 'business.json').read_text())
    ledger, sent = open_contracts(materials, registry)
    assert not ledger.compare(sent[0], '2026-03-01')['needs_notice']
    result = ledger.compare(sent[0], '2026-03-12')
    assert result['needs_notice']
    assert result['recorded_answer']['days'] == 7
    assert result['current_answer']['days'] == 4
    assert not ledger.compare(sent[1], '2026-03-12')['needs_notice']
