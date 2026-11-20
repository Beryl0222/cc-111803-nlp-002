import argparse
import json
from pathlib import Path

from .terms import ObligationDesk, SignedLibrary


def build_view(desk, library, base, region, service, work_date, knowledge_date):
    return {
        'knowledge_date': knowledge_date,
        'filed_documents': library.filed_documents(knowledge_date),
        'answer': desk.effective(base, region, service, work_date, knowledge_date),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='按服务地区、服务类型和履约日查询义务适用')
    parser.add_argument('region')
    parser.add_argument('service')
    parser.add_argument('work_date')
    parser.add_argument('--base', nargs=2, default=['MSA-1', '7'], metavar=('文号', '条款号'))
    parser.add_argument('--known', required=True, help='经办人今天查看材料的时点')
    parser.add_argument('--then', help='对照的历史查看时点')
    parser.add_argument('--materials', type=Path, default=Path('fixtures/desk.json'))
    parser.add_argument('--registry', type=Path, default=Path('fixtures/desk_registry.json'))
    args = parser.parse_args(argv)
    registered = json.loads(args.registry.read_text(encoding='utf-8'))
    materials = json.loads(args.materials.read_text(encoding='utf-8'))
    library = SignedLibrary(registered['documents'], materials['clauses'])
    desk = ObligationDesk(library)
    base = tuple(args.base)
    result = {
        'query': {'base': list(base), 'region': args.region, 'service': args.service, 'work_date': args.work_date},
        'current': build_view(desk, library, base, args.region, args.service, args.work_date, args.known),
    }
    if args.then:
        result['then'] = build_view(desk, library, base, args.region, args.service, args.work_date, args.then)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
