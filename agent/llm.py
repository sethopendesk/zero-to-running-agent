"""One place to switch models. Every node calls get_llm() and never imports a provider directly."""
import logging
import re
import time
import os

from langchain_core.language_models.chat_models import BaseChatModel

from agent import config


def _patient_gemini():
    """Gemini whose free tier says 'slow down' (429). Wait as long as Google asks, then try again."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_google_genai.chat_models import GoogleRateLimitError

    logging.getLogger("google_genai.models").setLevel(logging.ERROR)  # hide a harmless AFC notice

    class PatientGemini(ChatGoogleGenerativeAI):
        def _generate(self, *args, **kwargs):
            for attempt in range(5):
                try:
                    return super()._generate(*args, **kwargs)
                except GoogleRateLimitError as err:
                    if attempt == 4:
                        raise
                    hint = re.search(r"retry in ([\d.]+)s", str(err))
                    wait = float(hint.group(1)) + 2 if hint else 20
                    print(f"Gemini free tier is rate limited, waiting {wait:.0f}s then trying again...")
                    time.sleep(wait)

    return PatientGemini(model=config.GEMINI_MODEL, max_retries=2)


def get_llm() -> BaseChatModel | None:
    """Return the chat model for MODEL_PROVIDER, or None in mock mode."""
    if config.MODEL_PROVIDER == "mock":
        return None
    if config.MODEL_PROVIDER == "gemini":
        # The free tier allows about 15 requests a minute, so wait and retry on 429s.
        return _patient_gemini()
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=config.CLAUDE_MODEL,
                         max_retries=4,
                         max_tokens=4096,
                         default_headers={
                             "anthropic-workspace-id": os.environ["ANTHROPIC_WORKSPACE_ID"]
                         })
