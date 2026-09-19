import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 20
USER_AGENT = "bounty-intel/1.0 (+daily scope recon; personal use)"


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def get_json(session: requests.Session, url: str, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    response = session.get(url, **kwargs)
    response.raise_for_status()
    return response.json()
