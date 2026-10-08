"""
Medic AI — LLM Provider (Adaptador Multi-Proveedor)

Soporta Ollama (local), Google Gemini y OpenAI con una interfaz unificada.
Por defecto usa Ollama para ejecución 100% local.
"""
from __future__ import annotations

import json
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional

import httpx


# ══════════════════════════════════════
# Interfaz base
# ══════════════════════════════════════

class LLMProvider(ABC):
    """Interfaz unificada para todos los proveedores LLM."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 300,
    ) -> str:
        """Generación single-shot. Devuelve el texto completo."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 300,
    ) -> AsyncIterator[str]:
        """Generación en streaming. Yield de tokens uno a uno."""
        ...


# ══════════════════════════════════════
# Ollama (Local)
# ══════════════════════════════════════

class OllamaProvider(LLMProvider):
    """Proveedor local via Ollama HTTP API."""

    def __init__(self, model: str = "qwen3:8b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, messages, temperature=0.3, max_tokens=300) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def stream(self, messages, temperature=0.3, max_tokens=300) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if not data.get("done", False):
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue


# ══════════════════════════════════════
# Google Gemini
# ══════════════════════════════════════

class GeminiProvider(LLMProvider):
    """Proveedor Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        """Convierte formato OpenAI a formato Gemini."""
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                if system_instruction is None:
                    system_instruction = content
                else:
                    system_instruction += "\n" + content
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        return system_instruction, contents

    async def generate(self, messages, temperature=0.3, max_tokens=300) -> str:
        system_instruction, contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{self._base_url}/models/{self.model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return ""

    async def stream(self, messages, temperature=0.3, max_tokens=300) -> AsyncIterator[str]:
        system_instruction, contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{self._base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    text = p.get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            continue


# ══════════════════════════════════════
# OpenAI
# ══════════════════════════════════════

class OpenAIProvider(LLMProvider):
    """Proveedor OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._base_url = "https://api.openai.com/v1"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(self, messages, temperature=0.3, max_tokens=300) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def stream(self, messages, temperature=0.3, max_tokens=300) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line.strip() != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue


# ══════════════════════════════════════
# Factory
# ══════════════════════════════════════

def create_provider(
    provider_type: str,
    model: str,
    api_key: str = "",
    base_url: str = "http://localhost:11434",
) -> LLMProvider:
    """Factory para crear el proveedor LLM configurado."""
    if provider_type == "ollama":
        return OllamaProvider(model=model, base_url=base_url)
    elif provider_type == "gemini":
        if not api_key:
            raise ValueError("GEMINI_API_KEY es requerida para el proveedor Gemini")
        return GeminiProvider(api_key=api_key, model=model)
    elif provider_type == "openai":
        if not api_key:
            raise ValueError("OPENAI_API_KEY es requerida para el proveedor OpenAI")
        return OpenAIProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Proveedor LLM desconocido: {provider_type}")

