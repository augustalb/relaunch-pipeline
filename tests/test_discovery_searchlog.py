from pipeline.services.places import MockPlacesClient
from pipeline.stages import discovery


class CountingClient(MockPlacesClient):
    def __init__(self):
        super().__init__("http://127.0.0.1:9")
        self.queries = []

    def search(self, query, max_pages):
        self.queries.append(query)
        yield from super().search(query, max_pages)


def test_fully_processed_queries_are_not_repeated():
    first = CountingClient()
    s1 = discovery.run(client=first)
    assert first.queries and s1.get("skipped_recent_query", 0) == 0

    second = CountingClient()
    s2 = discovery.run(client=second)
    assert second.queries == []  # nothing paid twice
    assert s2["skipped_recent_query"] == len(first.queries)


def test_query_interrupted_by_limit_is_repeated():
    first = CountingClient()
    discovery.run(limit=1, client=first)
    interrupted = first.queries[-1]

    second = CountingClient()
    discovery.run(client=second)
    assert interrupted in second.queries
