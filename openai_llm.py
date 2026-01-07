"""
OpenAI LLM utility for calling GPT models using the Responses API.
Uses gpt-5-mini by default as recommended for cost-efficient tasks.
"""

from openai import OpenAI
import os
from typing import Optional, List, Dict, Union, TypeVar, Type
from pydantic import BaseModel

# Initialize the OpenAI client
# Will use OPENAI_API_KEY environment variable if set
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

T = TypeVar('T', bound=BaseModel)


def generate_response(
    input_text: Union[str, List[Dict[str, str]]],
    model: str = "gpt-5-mini",
    instructions: Optional[str] = None,
    reasoning: Optional[Dict[str, str]] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    prompt_id: Optional[str] = None,
    prompt_version: Optional[str] = None,
    prompt_variables: Optional[Dict] = None,
) -> str:
    """
    Generate a text response from the OpenAI model.
    
    Args:
        input_text: Either a string prompt or a list of message dicts with 'role' and 'content'
                   Example: "What is Python?" or [{"role": "user", "content": "What is Python?"}]
        model: Model to use (default: "gpt-5-mini")
        instructions: High-level instructions for the model (system-level guidance)
        reasoning: Dict with "effort" key for reasoning models (e.g., {"effort": "low"})
        max_tokens: Maximum tokens to generate (default: model's max)
        temperature: Sampling temperature (0-2, default: model default)
        prompt_id: ID of a reusable prompt from the dashboard
        prompt_version: Version of the prompt (defaults to current)
        prompt_variables: Variables to substitute in the prompt template
    
    Returns:
        The generated text output as a string
        
    Example:
        >>> response = generate_response("What is Python?")
        >>> print(response)
        
        >>> response = generate_response(
        ...     "Are semicolons optional in JavaScript?",
        ...     instructions="Talk like a pirate.",
        ...     reasoning={"effort": "low"}
        ... )
    """
    params = {
        "model": model,
    }
    
    # Handle prompt template if provided
    if prompt_id:
        params["prompt"] = {
            "id": prompt_id,
        }
        if prompt_version:
            params["prompt"]["version"] = prompt_version
        if prompt_variables:
            params["prompt"]["variables"] = prompt_variables
    else:
        # Use input_text directly
        params["input"] = input_text
    
    # Add optional parameters
    if instructions:
        params["instructions"] = instructions
    
    if reasoning:
        params["reasoning"] = reasoning
    
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    
    if temperature is not None:
        params["temperature"] = temperature
    
    try:
        response = client.responses.create(**params)
        return response.output_text
    except Exception as e:
        raise Exception(f"Error calling OpenAI API: {str(e)}")


def generate_response_with_messages(
    messages: List[Dict[str, str]],
    model: str = "gpt-5-mini",
    instructions: Optional[str] = None,
    reasoning: Optional[Dict[str, str]] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Generate a response using a list of messages with roles.
    
    Args:
        messages: List of message dicts, each with 'role' and 'content'
                 Roles can be: "user", "developer", "assistant"
                 Example: [
                     {"role": "developer", "content": "You are a helpful assistant."},
                     {"role": "user", "content": "What is Python?"}
                 ]
        model: Model to use (default: "gpt-5-mini")
        instructions: High-level instructions (alternative to developer messages)
        reasoning: Dict with "effort" for reasoning models
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
    
    Returns:
        The generated text output as a string
    """
    return generate_response(
        input_text=messages,
        model=model,
        instructions=instructions,
        reasoning=reasoning,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def generate_structured_response(
    input_text: Union[str, List[Dict[str, str]]],
    schema_model: Type[T],
    model: str = "gpt-5-mini",
    instructions: Optional[str] = None,
    reasoning: Optional[Dict[str, str]] = None,
    max_tokens: Optional[int] = None,  # Not used - responses.parse() doesn't support max_tokens
    temperature: Optional[float] = None,
) -> tuple[T, Optional[object]]:
    """
    Generate a structured response that adheres to a Pydantic model schema.
    
    Uses Structured Outputs to ensure the response matches your schema exactly.
    This is recommended over JSON mode for reliable schema adherence.
    
    Args:
        input_text: Either a string prompt or a list of message dicts with 'role' and 'content'
                   Example: "Extract event information." or 
                   [{"role": "user", "content": "Alice and Bob are going to a science fair on Friday."}]
        schema_model: A Pydantic BaseModel class that defines the expected output structure
        model: Model to use (default: "gpt-5-mini")
              Note: gpt-5-mini supports Structured Outputs
        instructions: High-level instructions for the model
        reasoning: Dict with "effort" key for reasoning models (e.g., {"effort": "low"})
        max_tokens: Not used - responses.parse() doesn't support output token limits
        temperature: Sampling temperature (0-2)
    
    Returns:
        A tuple of (parsed_model_instance, usage_object)
        - parsed_model_instance: An instance of the Pydantic model with the parsed response
        - usage_object: Usage object with token counts (input_tokens, output_tokens, total_tokens), or None
        
    Example:
        >>> from pydantic import BaseModel
        >>> 
        >>> class CalendarEvent(BaseModel):
        ...     name: str
        ...     date: str
        ...     participants: list[str]
        ... 
        >>> response = generate_structured_response(
        ...     "Alice and Bob are going to a science fair on Friday.",
        ...     CalendarEvent,
        ...     instructions="Extract the event information."
        ... )
        >>> print(response.name)
        >>> print(response.participants)
    """
    # Convert input_text to messages format if it's a string
    if isinstance(input_text, str):
        messages = [{"role": "user", "content": input_text}]
    else:
        messages = input_text
    
    params = {
        "model": model,
        "input": messages,
        "text_format": schema_model,
    }
    
    # Add optional parameters
    if instructions:
        params["instructions"] = instructions
    
    if reasoning:
        params["reasoning"] = reasoning
    
    # Note: responses.parse() doesn't support max_tokens/max_output_tokens parameter
    # Output is automatically constrained by the schema structure
    
    if temperature is not None:
        params["temperature"] = temperature
    
    try:
        response = client.responses.parse(**params)
        return response.output_parsed, response.usage if hasattr(response, 'usage') else None
    except Exception as e:
        raise Exception(f"Error calling OpenAI API with structured output: {str(e)}")


def get_embedding(
    text: Union[str, List[str]],
    model: str = "text-embedding-3-small",
    dimensions: Optional[int] = None,
    encoding_format: str = "float",
) -> Union[List[float], List[List[float]]]:
    """
    Get embeddings for text using OpenAI's embeddings API.
    
    Embeddings are vector representations of text that can be used for:
    - Search (rank results by relevance)
    - Clustering (group similar text)
    - Recommendations (find related items)
    - Classification (categorize text)
    
    Args:
        text: A single text string or a list of text strings to embed
        model: Embedding model to use (default: "text-embedding-3-small")
              Options: "text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"
        dimensions: Optional number of dimensions for the embedding (default: model's native size)
                   Can reduce from 1536 (small) or 3072 (large) to save storage/compute
        encoding_format: Format of the embedding ("float" or "base64", default: "float")
    
    Returns:
        If input is a single string: List of floats (the embedding vector)
        If input is a list of strings: List of lists of floats (one embedding per string)
        
    Example:
        >>> embedding = get_embedding("Your text here")
        >>> print(len(embedding))  # 1536 for text-embedding-3-small
        >>> 
        >>> embeddings = get_embedding(["Text 1", "Text 2", "Text 3"])
        >>> print(len(embeddings))  # 3
        >>> print(len(embeddings[0]))  # 1536
    """
    params = {
        "model": model,
        "input": text,
        "encoding_format": encoding_format,
    }
    
    if dimensions is not None:
        params["dimensions"] = dimensions
    
    try:
        response = client.embeddings.create(**params)
        
        # If single string, return single embedding
        if isinstance(text, str):
            return response.data[0].embedding
        else:
            # If list, return list of embeddings in order
            return [item.embedding for item in response.data]
            
    except Exception as e:
        raise Exception(f"Error calling OpenAI Embeddings API: {str(e)}")


def count_tokens(text: str, model: str = "gpt-5-mini") -> int:
    """
    Count the number of tokens in a text string.
    
    Note: This uses the tiktoken library for accurate token counting.
    For gpt-5-mini, we use the cl100k_base encoding (same as GPT-4).
    
    Args:
        text: The text to count tokens for
        model: The model name (for encoding selection)
    
    Returns:
        Number of tokens
    """
    try:
        import tiktoken
        # gpt-5-mini uses cl100k_base encoding (same as GPT-4)
        encoding = tiktoken.get_encoding("cl100k_base")
        # Some transcripts may contain strings that look like special tokens (e.g. "<|endoftext|>").
        # For cost estimation we want a best-effort count, not a hard failure.
        return len(encoding.encode(text, disallowed_special=()))
    except ImportError:
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4


if __name__ == "__main__":
    # Example usage
    print("Testing OpenAI LLM utility...")
    
    # Simple text generation
    response = generate_response("Say 'Hello, this is a test.'")
    print(f"\nSimple response: {response}")
    
    # With instructions
    response = generate_response(
        "What is Python?",
        instructions="Provide a concise, one-sentence answer."
    )
    print(f"\nWith instructions: {response}")
    
    # Structured output example
    try:
        class SimpleEvent(BaseModel):
            name: str
            date: str
            participants: list[str]
        
        structured_response, usage = generate_structured_response(
            "Alice and Bob are going to a science fair on Friday.",
            SimpleEvent,
            instructions="Extract the event information.",
            model="gpt-5-mini"  # gpt-5-mini supports structured outputs
        )
        print(f"\nStructured response:")
        print(f"  Name: {structured_response.name}")
        print(f"  Date: {structured_response.date}")
        print(f"  Participants: {structured_response.participants}")
        if usage:
            print(f"  Tokens: {usage.input_tokens} input + {usage.output_tokens} output = {usage.total_tokens} total")
    except Exception as e:
        print(f"\nStructured output test skipped: {e}")
    
    # Embeddings example
    try:
        embedding = get_embedding("Hello, this is a test.")
        print(f"\nEmbedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"\nEmbedding test skipped: {e}")
    
    # Token counting
    text = "Hello, this is a test."
    tokens = count_tokens(text)
    print(f"\nTokens in '{text}': {tokens}")

