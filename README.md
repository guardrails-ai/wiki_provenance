## Overview

| Developed by | Guardrails AI |
| --- | --- |
| Date of development | Feb 15, 2024 |
| Validator type | Format |
| Blog |  |
| License | Apache 2 |
| Input/Output | Output |

## Description

This validator checks if an LLM-generated text contains hallucinations. It retrieves the most relevant information from wikipedia and checks if the LLM-generated text is similar to the retrieved information using another LLM.

## Installation

```bash
$ guardrails hub install hub://guardrails/wiki-provenance
```

## Usage Examples

### Validating string output via Python

In this example, we use the `wiki-provenance` validator on any LLM generated text.

```python
# Import Guard and Validator
from guardrails.hub import WikiProvenance
from guardrails import Guard

# Initialize Validator
val = WikiProvenance(topic_name="Apple company")

# Setup Guard
guard = Guard.from_string(
    validators=[val, ...],
)

# Pass LLM output through guard
guard.parse("Apple was founded by Steve Jobs in April 1976.")  # Pass
guard.parse("Ratan Tata founded Apple in September 1998 as a fruit selling company.")  # Fail
```

## API Reference

`__init__`

- `on_fail`: The policy to enact when a validator fails.
