import json
from datetime import date

# 条款之间的关系：正文被补充协议在限定范围内替换，保留的例外和引用分别记载。
RELATION_NAMES = {'retains': '保留', 'refers': '引用'}


def iso(value):
    return date.fromisoformat(value)


class SignedLibrary:
    """签署文本库。文号加条款号定位条款，归档日决定经办人当时能看到哪些材料。"""

    def __init__(self, documents, clauses):
        self.documents = {document['id']: document for document in documents}
        self.clauses = {}
        for clause in clauses:
            key = clause['document'], clause['label']
            if key in self.clauses or key[0] not in self.documents:
                raise ValueError(f'条款重复或缺签署文件：{key}')
            self.clauses[key] = clause

    def filed_clause(self, key, knowledge_date):
        clause = self.clauses.get(key)
        if clause is None:
            return None
        document = self.documents[clause['document']]
        if iso(document['filed']) > knowledge_date:
            return None
        return clause

    def filed_documents(self, knowledge_date):
        known = iso(knowledge_date)
        filed = [document for document in self.documents.values() if iso(document['filed']) <= known]
        return [document['id'] for document in sorted(filed, key=lambda item: (iso(item['filed']), item['id']))]

    def find_label(self, label, knowledge_date):
        """同一编号可能被几版附件重复使用，按条款号收集当时可见的候选。"""
        found = []
        for key in self.clauses:
            if key[1] == label and self.filed_clause(key, knowledge_date) is not None:
                found.append(key)
        return sorted(found)

    def resolve_target(self, target, knowledge_date):
        """把条款里的引用目标定位到签署条款，返回（条款键或 None, 候选列表）。"""
        if isinstance(target, dict):
            if 'document' in target:
                target = (target['document'], target['label'])
            else:
                candidates = self.find_label(target['label'], knowledge_date)
                return (candidates[0] if len(candidates) == 1 else None), candidates
        key = tuple(target)
        if key in self.clauses and self.filed_clause(key, knowledge_date) is not None:
            return key, [key]
        return None, []


class ObligationDesk:
    """按服务地区、服务类型和履约日定位适用条款，并解释引用、限定、排除和保留。"""

    def __init__(self, library):
        self.library = library

    def effective(self, base, region, service, date_of_work, knowledge_date):
        base = tuple(base)
        when = iso(date_of_work)
        known = iso(knowledge_date)
        applicable = []
        for key, clause in self._chain(base, known):
            if not self._covers(clause, region, service):
                continue
            if iso(clause['effective']) <= when:
                applicable.append((key, clause))
        if not applicable:
            return None
        latest = max(iso(clause['effective']) for _, clause in applicable)
        selected = [(key, clause) for key, clause in applicable if iso(clause['effective']) == latest]
        if len(selected) != 1:
            raise ValueError('适用条款存在同日冲突')
        key, clause = selected[0]
        basis = [self._basis_entry(key, clause, '正文' if key == base else '替换')]
        related, review = self._walk_relations(key, clause, known)
        days = clause.get('days')
        exceptions = []
        for related_key, related_clause, kind, condition in related:
            entry = self._basis_entry(related_key, related_clause, RELATION_NAMES[kind])
            if condition:
                entry['condition'] = condition
            basis.append(entry)
            if kind == 'retains':
                exceptions.append({'clause': list(related_key), 'text': related_clause['text'], 'days': related_clause.get('days')})
            elif days is None and related_clause.get('days') is not None:
                days = related_clause['days']
        answer = {
            'status': 'needs_review' if review else 'ok',
            'clause': list(key),
            'text': clause['text'],
            'effective': clause['effective'],
            'days': days,
            'limits': {'regions': clause.get('regions', []), 'services': clause.get('services', [])},
            'exceptions': exceptions,
            'basis': basis,
        }
        if clause.get('excludes'):
            answer['excludes'] = clause['excludes']
        if review:
            answer['review'] = review
        return answer

    def _chain(self, base, known):
        """正文加各级补充协议。替换范围按条款记载逐层展开，未归档的条款不进结果。"""
        chain = []
        seen = set()
        frontier = [base]
        while frontier:
            key = frontier.pop()
            if key in seen or key not in self.library.clauses:
                continue
            seen.add(key)
            clause = self.library.clauses[key]
            for other_key, other in self.library.clauses.items():
                if tuple(other.get('replaces', ())) == key:
                    frontier.append(other_key)
            if self.library.filed_clause(key, known) is not None:
                chain.append((key, clause))
        return chain

    @staticmethod
    def _covers(clause, region, service):
        if region not in clause.get('regions', ()) or service not in clause.get('services', ()):
            return False
        excludes = clause.get('excludes', {})
        return region not in excludes.get('regions', ()) and service not in excludes.get('services', ())

    def _basis_entry(self, key, clause, relation):
        document = self.library.documents[clause['document']]
        return {
            'clause': list(key),
            'relation': relation,
            'text': clause['text'],
            'effective': clause['effective'],
            'filed': document['filed'],
        }

    def _walk_relations(self, start_key, start_clause, known):
        """沿保留、引用关系走到被引条款。多个候选或例外条件互相引用时交回核对。"""
        related = []
        review = None
        visited = {start_key}
        stack = [(start_key, start_clause, [start_key])]
        while stack:
            key, clause, path = stack.pop()
            for kind in ('retains', 'refers'):
                for raw in clause.get(kind, []):
                    target, condition = _split_target(raw)
                    resolved, candidates = self.library.resolve_target(target, known)
                    if resolved is None:
                        review = review or _review_target(kind, raw, candidates)
                        continue
                    if resolved in path:
                        review = review or {
                            'reason': '例外条件互相引用，缺少可用起点',
                            'cycle': [list(step) for step in path + [resolved]],
                        }
                        continue
                    if resolved in visited:
                        continue
                    visited.add(resolved)
                    following = self.library.clauses[resolved]
                    related.append((resolved, following, kind, condition))
                    stack.append((resolved, following, path + [resolved]))
        return related, review


def _split_target(raw):
    if isinstance(raw, dict):
        condition = raw.get('condition')
        if 'document' in raw:
            return (raw['document'], raw['label']), condition
        return {'label': raw['label']}, condition
    return tuple(raw), None


def _review_target(kind, raw, candidates):
    if candidates:
        return {
            'reason': '被引条款存在多个候选',
            'relation': RELATION_NAMES[kind],
            'candidates': [list(candidate) for candidate in candidates],
        }
    return {'reason': '被引条款无法定位', 'relation': RELATION_NAMES[kind], 'target': raw}


def _substance(answer):
    """经办人实际承担的义务：期限和保留的例外。改编号或换说法不影响比较。"""
    if answer is None:
        return None
    exceptions = sorted(
        ({'days': exception.get('days')} for exception in answer.get('exceptions', [])),
        key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
    )
    return {'days': answer.get('days'), 'exceptions': exceptions}


def _differences(previous, current):
    if previous == current:
        return []
    if previous is None or current is None:
        return [{'aspect': '适用性', 'before': previous, 'after': current}]
    differences = []
    if previous['days'] != current['days']:
        differences.append({'aspect': '期限', 'before': previous['days'], 'after': current['days']})
    if previous['exceptions'] != current['exceptions']:
        differences.append({'aspect': '例外', 'before': previous['exceptions'], 'after': current['exceptions']})
    return differences


class RenewalLedger:
    """复核已发解释：义务实质没变就不重发，期限或例外真变就定位差异。"""

    def __init__(self, desk):
        self.desk = desk

    def compare(self, sent, date_known):
        current = self.desk.effective(tuple(sent['key']), sent['region'], sent['service'], sent['service_date'], date_known)
        previous = sent['answer']
        differences = _differences(_substance(previous), _substance(current))
        needs_review = bool(current and current.get('status') == 'needs_review')
        if needs_review:
            disposal = '交回核对'
        elif differences:
            disposal = '补充说明'
        else:
            disposal = '继续办理'
        return {
            'id': sent['id'],
            'recorded_answer': previous,
            'current_answer': current,
            'needs_notice': bool(differences),
            'needs_review': needs_review,
            'differences': differences,
            'disposal': disposal,
        }
