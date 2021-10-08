from .instrumentation import instrument_document


class IdentityMap:
    def __init__(self):
        self._idmap = {}

    def process(self, collection, doc, status):
        """Process and insert a single 'raw' doc from MongoDB"""
        key = (collection, doc["_id"])
        result = self._idmap[key] = instrument_document(
            doc, status, collection
        )
        return result

    def get(self, collection, _id, default=None):
        return self._idmap.get((collection, _id), default)
