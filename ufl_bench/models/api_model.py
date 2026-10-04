"""Pluggable API Model Adapter for LLMs (OpenAI-compatible and Gemini endpoints)."""

import os
import json
from typing import Any, Dict, List, Optional, Union
from .base import BaseModelAdapter, ModelResponse, ToolCall, Message
from ..utils.ast_parser import extract_ast_calls


class OpenAICompatibleAdapter(BaseModelAdapter):
    """Adapter for OpenAI-compatible inference endpoints (vLLM, Ollama, OpenAI, DeepSeek, etc.)."""

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(model_name, **kwargs)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def generate(
        self,
        messages: List[Union[Dict[str, Any], Message]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        **kwargs
    ) -> ModelResponse:
        import urllib.request
        import urllib.error

        formatted_msgs = []
        for m in messages:
            if isinstance(m, Message):
                formatted_msgs.append(m.to_dict())
            else:
                formatted_msgs.append(m)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]
                msg = choice.get("message", {})
                content = msg.get("content") or ""
                tool_calls_raw = msg.get("tool_calls", [])

                parsed_tool_calls: List[ToolCall] = []
                for tc in tool_calls_raw:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    fn_args_raw = fn.get("arguments", "{}")
                    try:
                        fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
                    except Exception:
                        fn_args = {}
                    parsed_tool_calls.append(ToolCall(name=fn_name, arguments=fn_args, id=tc.get("id")))

                # If no native tool calls returned in schema, extract via AST from content
                if not parsed_tool_calls and content and tools:
                    ast_extracted = extract_ast_calls(content, tools)
                    for call in ast_extracted:
                        if call.is_valid_syntax:
                            parsed_tool_calls.append(ToolCall(name=call.name, arguments=call.arguments))

                usage = data.get("usage", {})
                return ModelResponse(
                    content=content,
                    tool_calls=parsed_tool_calls,
                    raw=data,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    finish_reason=choice.get("finish_reason"),
                )
        except Exception as e:
            return ModelResponse(
                content="",
                tool_calls=[],
                raw={"error": str(e)},
                metadata={"error": str(e)},
            )
