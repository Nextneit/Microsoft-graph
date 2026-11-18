import requests

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get(self, path: str, params: dict | None = None) -> dict:
        r = self.session.get(f"{GRAPH}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_all(self, path: str, params: dict | None = None):
        """Itera todos los resultados siguiendo @odata.nextLink."""
        url = f"{GRAPH}{path}"
        while url:
            r = self.session.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            yield from data.get("value", [])
            url = data.get("@odata.nextLink")
            params = None  # el nextLink ya incluye los parámetros