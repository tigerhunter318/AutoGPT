from __future__ import annotations

import time
from typing import List, Optional

import openai
from colorama import Fore
from openai.error import APIError, RateLimitError

from autogpt.config import Config
from autogpt.types.openai import Message

CFG = Config()

openai.api_key = CFG.openai_api_key


def call_ai_function(
    function: str, args: list, description: str, model: str | None = None
) -> str:
    """Call an AI function

    This is a magic function that can do anything with no-code. See
    https://github.com/Torantulino/AI-Functions for more info.

    Args:
        function (str): The function to call
        args (list): The arguments to pass to the function
        description (str): The description of the function
        model (str, optional): The model to use. Defaults to None.

    Returns:
        str: The response from the function
    """
    if model is None:
        model = CFG.smart_llm_model
    # For each arg, if any are None, convert to "None":
    args = [str(arg) if arg is not None else "None" for arg in args]
    # parse args to comma separated string
    args: str = ", ".join(args)
    messages: List[Message] = [
        {
            "role": "system",
            "content": f"You are now the following python function: ```# {description}"
            f"\n{function}```\n\nOnly respond with your `return` value.",
        },
        {"role": "user", "content": args},
    ]

    return create_chat_completion(model=model, messages=messages, temperature=0)


# Overly simple abstraction until we create something better
# simple retry mechanism when getting a rate error or a bad gateway
def create_chat_completion(
    messages: List[Message],  # type: ignore
    model: Optional[str] = None,
    temperature: float = CFG.temperature,
    max_tokens: Optional[int] = None,
) -> str:
    """Create a chat completion using the OpenAI API

    Args:
        messages (List[Message]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.

    Returns:
        str: The response from the chat completion
    """
    num_retries = 10
    if CFG.debug_mode:
        print(
            f"{Fore.GREEN}Creating chat completion with model {model}, temperature {temperature}, max_tokens {max_tokens}{Fore.RESET}"
        )
    for plugin in CFG.plugins:
        if plugin.can_handle_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            return plugin.handle_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
    response = None
    for attempt in range(num_retries):
        backoff = 2 ** (attempt + 2)
        try:
            if CFG.use_azure:
                response = openai.ChatCompletion.create(
                    deployment_id=CFG.get_azure_deployment_id_for_model(model),
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            else:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            break
        except RateLimitError:
            if CFG.debug_mode:
                print(
                    f"{Fore.RED}Error: ", f"Reached rate limit, passing...{Fore.RESET}"
                )
        except APIError as e:
            if e.http_status != 502:
                raise
            if attempt == num_retries - 1:
                raise
        if CFG.debug_mode:
            print(
                f"{Fore.RED}Error: ",
                f"API Bad gateway. Waiting {backoff} seconds...{Fore.RESET}",
            )
        time.sleep(backoff)
    if response is None:
        raise RuntimeError(f"Failed to get response after {num_retries} retries")
    resp = response.choices[0].message["content"]
    for plugin in CFG.plugins:
        if not plugin.can_handle_on_response():
            continue
        resp = plugin.on_response(resp)
    return resp


def create_embedding_with_ada(text) -> list:
    """Create a embedding with text-ada-002 using the OpenAI SDK"""
    num_retries = 10
    for attempt in range(num_retries):
        backoff = 2 ** (attempt + 2)
        try:
            if CFG.use_azure:
                return openai.Embedding.create(
                    input=[text],
                    engine=CFG.get_azure_deployment_id_for_model(
                        "text-embedding-ada-002"
                    ),
                )["data"][0]["embedding"]
            else:
                return openai.Embedding.create(
                    input=[text], model="text-embedding-ada-002"
                )["data"][0]["embedding"]
        except RateLimitError:
            pass
        except APIError as e:
            if e.http_status != 502:
                raise
            if attempt == num_retries - 1:
                raise
        if CFG.debug_mode:
            print(
                f"{Fore.RED}Error: ",
                f"API Bad gateway. Waiting {backoff} seconds...{Fore.RESET}",
            )
        time.sleep(backoff)
