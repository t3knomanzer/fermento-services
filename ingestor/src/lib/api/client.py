from typing import Any, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIClient:
    """
    Lightweight client for the Fermento REST API.
    Methods return parsed JSON (dict / list) or raise requests.HTTPError on non-2xx.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        token: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

        retries = Retry(
            total=max_retries, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504)
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = self._url(path)
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.request(method, url, **kwargs)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            # Attach response content for easier debugging
            raise requests.HTTPError(
                f"{response.status_code} {response.reason}: {response.text}",
                response=response,
            )
        if response.status_code == 204:
            return None
        # Assume JSON responses
        return response.json()

    # Generic CRUD helpers (resource is e.g. "starters", "jars", "flours", "flour_blends",
    # "feeding_samples", "feeding_events")
    def list_resources(
        self, resource: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        return self._request("GET", f"/{resource}", params=params)

    def get_resource(self, resource: str, resource_id: Any) -> Any:
        return self._request("GET", f"/{resource}/{resource_id}")

    def create_resource(self, resource: str, payload: Dict[str, Any]) -> Any:
        return self._request("POST", f"/{resource}", json=payload)

    def update_resource(
        self, resource: str, resource_id: Any, payload: Dict[str, Any]
    ) -> Any:
        return self._request("PUT", f"/{resource}/{resource_id}", json=payload)

    def patch_resource(
        self, resource: str, resource_id: Any, payload: Dict[str, Any]
    ) -> Any:
        return self._request("PATCH", f"/{resource}/{resource_id}", json=payload)

    def delete_resource(self, resource: str, resource_id: Any) -> Any:
        return self._request("DELETE", f"/{resource}/{resource_id}")

    # Convenience wrappers for known API entities
