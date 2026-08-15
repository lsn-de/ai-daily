"""OpenAI 兼容客户端封装"""
import json
import os
import re

_client = None


def get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise SystemExit("未配置 OPENAI_API_KEY，请复制 .env.example 为 .env 并填写")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _extract_json(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # 兜底：截取第一个 {...} 或 [...]
    m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"模型未返回合法 JSON: {text[:200]}")


def chat_json(cfg: dict, system: str, user: str) -> dict | list:
    """发起对话并解析 JSON 返回"""
    client = get_client()
    llm_cfg = cfg["llm"]
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs = dict(
        model=llm_cfg["model"],
        messages=messages,
        temperature=llm_cfg["temperature"],
        max_tokens=llm_cfg["max_tokens"],
    )
    try:
        resp = client.chat.completions.create(
            response_format={"type": "json_object"}, **kwargs)
    except Exception:
        # 部分兼容端点不支持 response_format，降级重试
        resp = client.chat.completions.create(**kwargs)
    return _extract_json(resp.choices[0].message.content or "")
