from datetime import date


def iso(value):
    return date.fromisoformat(value)


class SignedLibrary:
    def __init__(self, documents, clauses):
        self.documents = {document['id']: document for document in documents}
        self.clauses = {}
        for clause in clauses:
            key = clause['document'], clause['label']
            if key in self.clauses or key[0] not in self.documents:
                raise ValueError(f'条款重复或缺签署文件：{key}')
            self.clauses[key] = clause

    def filed_clause(self, key, knowledge_date):
        clause = self.clauses[key]
        document = self.documents[clause['document']]
        if iso(document['filed']) > knowledge_date:
            return None
        return clause


class ObligationDesk:
    def __init__(self, library):
        self.library = library

    def effective(self, base, region, service, date_of_work, knowledge_date):
        when = iso(date_of_work)
        known = iso(knowledge_date)
        applicable = []
        for key, clause in self.library.clauses.items():
            if key != base and tuple(clause.get('replaces', ())) != base:
                continue
            if self.library.filed_clause(key, known) is None:
                continue
            if region not in clause['regions'] or service not in clause['services']:
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
        return {'clause': list(key), 'text': clause['text'], 'days': clause['days']}


class RenewalLedger:
    def __init__(self, desk):
        self.desk = desk

    def compare(self, sent, date_known):
        parameters = sent['key'], sent['region'], sent['service'], sent['service_date']
        current = self.desk.effective(tuple(parameters[0]), *parameters[1:], date_known)
        previous = sent['answer']
        return {'id': sent['id'], 'recorded_answer': previous, 'current_answer': current,
                'needs_notice': current != previous}
