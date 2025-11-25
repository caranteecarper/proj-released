import os
import time
from typing import List

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tmt.v20180321 import tmt_client, models


class TencentTextTranslator:
    """
    Lightweight wrapper around Tencent Cloud TextTranslate.

    - Supports simple rate limiting.
    - Splits long text into chunks (default max_len ~ 4500 chars).
    - Exposes a single translate_text method.
    """

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-beijing",
        project_id: int = 0,
        max_len: int = 4500,
        qps: float = 4.5,
        endpoint: str = "tmt.tencentcloudapi.com",
    ) -> None:
        self.project_id = project_id
        self.max_len = max_len
        self.min_interval = 1.0 / qps if qps and qps > 0 else 0.0
        self._last_ts = 0.0

        cred = credential.Credential(secret_id, secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = endpoint
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        self.client = tmt_client.TmtClient(cred, region, client_profile)

    def translate_text(self, text: str, source: str = "auto", target: str = "zh") -> str:
        if not text:
            return ""
        chunks = self._split_text(text, self.max_len)
        translated_parts: List[str] = []
        for part in chunks:
            self._sleep_if_needed()
            req = models.TextTranslateRequest()
            req.SourceText = part
            req.Source = source
            req.Target = target
            req.ProjectId = self.project_id
            resp = self.client.TextTranslate(req)
            translated_parts.append(resp.TargetText)
            self._last_ts = time.time()
        return "".join(translated_parts)

    def _sleep_if_needed(self) -> None:
        if self.min_interval <= 0:
            return
        now = time.time()
        elapsed = now - self._last_ts
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    @staticmethod
    def _split_text(text: str, max_len: int) -> List[str]:
        if len(text) <= max_len:
            return [text]
        parts: List[str] = []
        buf: List[str] = []
        buf_len = 0
        for line in text.splitlines(True):  # keep line breaks
            line_len = len(line)
            if buf_len + line_len > max_len and buf:
                parts.append("".join(buf))
                buf = []
                buf_len = 0
            if line_len > max_len:
                # force split an overlong single line
                start = 0
                while start < line_len:
                    end = min(start + max_len, line_len)
                    chunk = line[start:end]
                    if chunk:
                        parts.append(chunk)
                    start = end
                buf = []
                buf_len = 0
                continue
            buf.append(line)
            buf_len += line_len
        if buf:
            parts.append("".join(buf))
        return parts


def build_translator_from_env(
    default_region: str = "ap-beijing",
    project_id: int = 0,
    max_len: int = 4500,
    qps: float = 4.5,
) -> TencentTextTranslator:
    secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID") or os.environ.get("SECRET_ID")
    secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not secret_id or not secret_key:
        raise RuntimeError("Missing credentials: set TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY.")
    region = os.environ.get("TENCENTCLOUD_REGION", default_region)
    return TencentTextTranslator(
        secret_id=secret_id,
        secret_key=secret_key,
        region=region,
        project_id=project_id,
        max_len=max_len,
        qps=qps,
    )
