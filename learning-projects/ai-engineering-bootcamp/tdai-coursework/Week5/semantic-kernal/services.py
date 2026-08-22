# Copyright (c) Microsoft. All rights reserved.
# Semantic Kernel sample helper - Service enum

from enum import Enum


class Service(Enum):
    """Services available for Semantic Kernel demo notebooks."""

    OpenAI = "openai"
    AzureOpenAI = "azureopenai"
    HuggingFace = "huggingface"
