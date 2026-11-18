import argparse
import json
from pathlib import Path

from .terms import ObligationDesk, RenewalLedger, SignedLibrary


def open_contracts(materials, registered):
    library = SignedLibrary(registered['documents'], materials['clauses'])
    return RenewalLedger(ObligationDesk(library)), materials['sent']


def main():
    parser = argparse.ArgumentParser(description='复核已经发送的续约解释')
    parser.add_argument('date_known')
    parser.add_argument('--materials', type=Path, default=Path('fixtures/renewal.json'))
    parser.add_argument('--registry', type=Path, default=Path('fixtures/business.json'))
    args = parser.parse_args()
    ledger, answers = open_contracts(json.loads(args.materials.read_text()), json.loads(args.registry.read_text()))
    print(json.dumps([ledger.compare(answer, args.date_known) for answer in answers], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
