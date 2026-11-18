import json
from pathlib import Path

def load_facts(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def summarize(facts):
    return sorted(document['id'] for document in facts['documents'] if document['filed'] <= facts['as_of'])
