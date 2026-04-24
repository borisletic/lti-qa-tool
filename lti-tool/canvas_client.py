"""
Canvas API Client
Dohvata fajlove iz Canvas kursa preko Canvas REST API-ja.

Autentifikacija: Developer Token (Personal Access Token)
Token se generiše u Canvas-u: Account → Settings → Approved Integrations → + New Access Token

Referenca: https://canvas.instructure.com/doc/api/files.html
"""

import os
import io
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests

logger = logging.getLogger(__name__)


class CanvasClient:
    """
    Klijent za Canvas REST API sa fokusom na fajlove u kursu.
    """

    # Ekstenzije koje tool zna da procesira (mora se poklopiti sa
    # extract_text_from_file metodom ispod)
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf', '.docx'}

    def __init__(self, base_url: str = None, api_token: str = None):
        """
        Args:
            base_url: Canvas URL (npr. http://canvas:80 za Docker network,
                     ili http://localhost:3000 za eksterni pristup).
                     Default: CANVAS_API_URL env varijabla.
            api_token: Canvas Developer Token.
                      Default: CANVAS_API_TOKEN env varijabla.
        """
        self.base_url = (base_url or os.environ.get('CANVAS_API_URL', '')).rstrip('/')
        self.api_token = api_token or os.environ.get('CANVAS_API_TOKEN', '')

        if not self.base_url:
            raise ValueError(
                "Canvas base_url nije postavljen. "
                "Postaviti CANVAS_API_URL env varijablu."
            )
        if not self.api_token:
            raise ValueError(
                "Canvas API token nije postavljen. "
                "Generisati Developer Token u Canvas-u i postaviti "
                "CANVAS_API_TOKEN env varijablu."
            )

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Accept': 'application/json',
        })

    # -------------------------------------------------------------------
    # API helpers
    # -------------------------------------------------------------------

    def _api_get(self, path: str, params: Optional[Dict] = None) -> requests.Response:
        """GET request na Canvas API sa error handling-om."""
        url = urljoin(self.base_url + '/', path.lstrip('/'))
        logger.debug(f"Canvas API GET: {url} params={params}")
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp

    def _paginated_get(self, path: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Canvas paginira rezultate preko Link header-a (RFC 5988).
        Prati 'next' link dok ne iscrpe sve stranice.
        """
        params = dict(params or {})
        params.setdefault('per_page', 100)

        results = []
        url = urljoin(self.base_url + '/', path.lstrip('/'))

        while url:
            logger.debug(f"Canvas API paginated GET: {url}")
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            page = resp.json()
            if not isinstance(page, list):
                # Defenzivno — ako API vrati dict sa error-om
                logger.warning(f"Unexpected paginated response: {page}")
                break
            results.extend(page)

            # params se šalju samo prvi put — next URL već sadrži sve query params
            params = None
            url = self._next_link(resp)

        return results

    @staticmethod
    def _next_link(resp: requests.Response) -> Optional[str]:
        """Parsuje Link header i vraća 'next' URL ako postoji."""
        link_header = resp.headers.get('Link', '')
        if not link_header:
            return None
        for part in link_header.split(','):
            segments = part.strip().split(';')
            if len(segments) < 2:
                continue
            url_part = segments[0].strip()
            rel_part = segments[1].strip()
            if rel_part == 'rel="next"' and url_part.startswith('<') and url_part.endswith('>'):
                return url_part[1:-1]
        return None

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def test_connection(self) -> Tuple[bool, str]:
        """
        Testira konekciju i token. Vraća (ok, poruka).
        """
        try:
            resp = self._api_get('/api/v1/users/self')
            user = resp.json()
            return True, f"Konektovano kao: {user.get('name', 'N/A')} (id={user.get('id')})"
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else '?'
            return False, f"HTTP {status}: {e}"
        except Exception as e:
            return False, f"Greška: {e}"

    def list_course_files(self, course_id: str) -> List[Dict]:
        """
        Vraća listu svih fajlova u kursu.

        Svaki fajl ima barem: id, display_name, filename, url, size,
        content-type, updated_at.

        Referenca: GET /api/v1/courses/:course_id/files
        """
        path = f'/api/v1/courses/{course_id}/files'
        try:
            files = self._paginated_get(path)
            logger.info(f"Canvas course {course_id}: pronađeno {len(files)} fajlova")
            return files
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else '?'
            logger.error(f"list_course_files failed ({status}): {e}")
            raise

    def _rewrite_to_internal(self, url: str) -> str:
        """
        Canvas vraca pre-signed download URL-ove sa hostom iz domain.yml
        (npr. http://localhost:3000/files/6/download?...). Iz Docker mreze
        taj host nije dostupan — Canvas je 'http://canvas:80'. Zato
        prepisemo scheme/host/port pre nego sto pozovemo URL.

        Verifier query parametar ostaje nepromenjen — on autorizuje download.
        """
        parsed = urlparse(url)
        internal = urlparse(self.base_url)
        rewritten = parsed._replace(
            scheme=internal.scheme,
            netloc=internal.netloc,
        )
        return urlunparse(rewritten)

    def _external_host_header(self, original_url: str) -> str:
        """
        Vraca host:port iz originalnog URL-a (ono sto Canvas ocekuje
        u Host header-u). Canvas radi host enforcement i 302-uje na svoj
        kanonski host ako se to ne posalje.
        """
        parsed = urlparse(original_url)
        return parsed.netloc

    def download_file(self, file_info: Dict, max_redirects: int = 5) -> bytes:
        """
        Skida sadržaj fajla kao bytes.

        Canvas file['url'] je pre-signed URL — verifier u query string-u
        autorizuje download, pa ne treba Authorization header.

        Trik: Canvas radi host enforcement (gleda Host header, i ako nije
        kanonski domen iz domain.yml — npr. 'localhost:3000' — vraca 302 na
        kanonski URL). Iz Docker mreze nemamo TCP konekciju ka 'localhost:3000',
        ali imamo ka 'canvas:80'. Zato:
          - TCP ide na internal host (canvas:80) — sto rewrite radi
          - Host header eksplicitno postavljamo na ono sto Canvas ocekuje
            (localhost:3000 iz originalnog URL-a)
        Tako Canvas misli da request stize na 'svoj' domen i ne redirect-uje.
        """
        download_url = file_info.get('url')
        if not download_url:
            raise ValueError(f"File {file_info.get('id')} nema download URL")

        external_host = self._external_host_header(download_url)
        url = self._rewrite_to_internal(download_url)

        for hop in range(max_redirects):
            logger.debug(f"Download hop {hop}: {url} (Host: {external_host})")
            resp = requests.get(
                url,
                timeout=60,
                allow_redirects=False,
                headers={'Host': external_host},
            )

            if resp.status_code in (301, 302, 303, 307, 308):
                next_url = resp.headers.get('Location')
                if not next_url:
                    raise ValueError(f"Redirect bez Location header-a od {url}")
                if not urlparse(next_url).netloc:
                    next_url = urljoin(url, next_url)
                # Update i Host header za novi URL (moze biti drugi domen)
                external_host = urlparse(next_url).netloc
                url = self._rewrite_to_internal(next_url)
                continue

            resp.raise_for_status()
            return resp.content

        raise ValueError(f"Previse redirect-a (>{max_redirects}) za fajl {file_info.get('id')}")

    # -------------------------------------------------------------------
    # Text extraction
    # -------------------------------------------------------------------

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        """Da li znamo da procesiramo ovaj tip fajla."""
        ext = cls._extension(filename)
        return ext in cls.SUPPORTED_EXTENSIONS

    @staticmethod
    def _extension(filename: str) -> str:
        if '.' not in filename:
            return ''
        return '.' + filename.rsplit('.', 1)[1].lower()

    @classmethod
    def extract_text(cls, filename: str, content: bytes) -> str:
        """
        Ekstraktuje tekst iz fajla na osnovu ekstenzije.
        Podiže ValueError za nepodržane formate.

        NAPOMENA: Logika za svaki format mora da odgovara ekstenzijama
        u SUPPORTED_EXTENSIONS iznad.
        """
        ext = cls._extension(filename)

        if ext in ('.txt', '.md'):
            return content.decode('utf-8', errors='ignore')

        if ext == '.pdf':
            # PyPDF2 je već dependency (vidi requirements.txt)
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        pages.append(text)
                except Exception as e:
                    logger.warning(f"PDF page {i} extract failed: {e}")
            return '\n\n'.join(pages)

        if ext == '.docx':
            from docx import Document
            doc = Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return '\n\n'.join(paragraphs)

        raise ValueError(f"Nepodržan format: {ext}")
