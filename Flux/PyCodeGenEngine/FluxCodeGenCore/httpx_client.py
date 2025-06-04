import requests
from typing import Dict, Any, Optional
import logging
from requests.adapters import HTTPAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIClient:
    def __init__(
            self,
            base_url: str = '/',
            default_headers: Dict[str, str] = None,
            timeout: int = 30
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL for API calls
            default_headers: Default headers for all requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self.session.mount('http://', self.adapter)
        self.session.mount('https://', self.adapter)

        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            **(default_headers or {})
        })

    def _make_request(
            self,
            method: str,
            endpoint: str,
            params: Dict = None,
            json: Dict = None,
            data: Any = None,
            headers: Dict = None,
            **kwargs
    ) -> requests.Response:
        """Make HTTP request."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Send GET request."""
        return self._make_request('GET', endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Send POST request."""
        return self._make_request('POST', endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Send PUT request."""
        return self._make_request('PUT', endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> requests.Response:
        """Send PATCH request."""
        return self._make_request('PATCH', endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Send DELETE request."""
        return self._make_request('DELETE', endpoint, **kwargs)

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


default_httpx_client = APIClient()