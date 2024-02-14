from typing import Callable, Dict, Optional
from warnings import warn

from guardrails.validator_base import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

import chromadb
from litellm import completion
import wikipedia
import nltk


@register_validator(name="guardrails/wiki_provenance", data_type="string")
class WikiProvenance(Validator):
    """Validates that an LLM response is true based on Wikipedia data.

    The conversation topic is used to fetch the Wikipedia page and
    the LLM response is validated based on the Wikipedia page content.
    The topic is explcitly provided by the user.

    Note for users:
    Please be specific with the topic name to avoid disambiguation errors and
    to retrieve the most relevant Wikipedia page.

    **Key Properties**

    | Property                      | Description                       |
    | ----------------------------- | --------------------------------- |
    | Name for `format` attribute   | `guardrails/wiki_provenance`      |
    | Supported data types          | `string`                          |
    | Programmatic fix              | Return supported sentences only   |
    """  # noqa

    def __init__(
        self,
        topic_name: str,
        validation_method: str = "sentence",
        llm_callable: str = "gpt-3.5-turbo",  # LiteLLM model name
        on_fail: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(
            on_fail,
            topic_name=topic_name,
            validation_method=validation_method,
            llm_callable=llm_callable,
            **kwargs,
        )
        self.topic_name = topic_name
        self.validation_method = validation_method
        self.llm_callable = llm_callable

        # Instantiate chromadb client and create a collection
        chroma_client = chromadb.Client()
        self.collection = chroma_client.get_or_create_collection(
            name=f"wiki_{str(hash(self.topic_name))}",
        )

        # Get the Wikipedia page, chunk it up, and add it to vector DB
        self.page = self.get_wiki_page()
        self.add_to_collection(self.page.content)

    def get_wiki_page(self):
        """Set the Wikipedia page."""

        # Search for the Wikipedia page
        search_results = wikipedia.search(self.topic_name, results=3)
        print(search_results)
        page = None
        for search_result in search_results:
            try:
                page = wikipedia.page(title=search_result, auto_suggest=False)
                break
            except wikipedia.exceptions.DisambiguationError as de:
                # If disambiguation error, resolve with the first option
                warn(
                    f"Resolving disambiguation error with the first option: {de.options[0]} "
                    "In future, please be more specific."
                )
                page = wikipedia.page(title=de.options[0], auto_suggest=False)
                break
            except wikipedia.exceptions.PageError:
                # If page error, continue to the next search result
                continue

        # Raise an error if a valid Wikipedia page is not found
        if page is None:
            raise RuntimeError(
                f"Could not find a valid Wikipedia page for {self.topic_name}. "
                "Please try with a different topic."
            )
        return page

    def join_single_sentence_chunks(self, chunks) -> list[str]:
        """
        Joins consecutive single-sentence chunks in a list to form paragraphs.

        Args:
        chunks: A list of strings representing text chunks.

        Returns:
        A new list with paragraphs formed by joining consecutive single-sentence chunks.
        """
        new_chunks = []
        paragraph = ""
        for chunk in chunks:
            # Check if the chunk is a single sentence
            if chunk.count(".") <= 1:
                paragraph += " " + chunk
            else:
                # If not a single sentence,
                # end the previous paragraph and add it to the list
                if paragraph:
                    new_chunks.append(paragraph.strip())

                # Start a new paragraph
                paragraph = chunk

        # Add the last paragraph if exists
        if paragraph:
            new_chunks.append(paragraph.strip())
        return new_chunks

    def get_page_chunks(self, page_content: str) -> list[str]:
        """Transforms the Wikipedia page content into paragraphs.

        Args:
            page_content (str): Wikipedia page content.

        Returns:
            chunks (List[str]): A list of paragraphs of the Wikipedia page.
        """
        # Split based on newline
        chunks = page_content.split("\n")

        # Some cleaning
        chunks = [
            chunk
            for chunk in chunks
            if not chunk.startswith("==")
            and not chunk.startswith("===")
            and chunk.strip() != ""
        ]

        # Join consecutive single-sentence chunks to form paragraphs
        chunks = self.join_single_sentence_chunks(chunks)
        return chunks

    def add_to_collection(self, page_content: str) -> None:
        """Adds the Wikipedia page content to a vector collection.

        ETL step that extracts the content from the Wikipedia page,
        transforms it into paragraphs, and loads it to the vector DB.

        Args:
            page_content (str): Wikipedia page content.
        """
        chunks = self.get_page_chunks(page_content)

        # Add the chunks to the collection
        self.collection.add(
            documents=chunks,
            ids=[f"{i}" for i in range(len(chunks))],
        )

    def get_closest_chunks(self, response: str) -> list[str]:
        """Retrieves the closest matching paragraphs to the LLM response

        Args:
            response (str): LLM response.

        Returns:
            closest_chunks (List[str]): A list of the closest matching paragraphs to the LLM response.
        """
        # Get the closest matching chunks to the LLM response
        results = self.collection.query(
            query_texts=[response],
            n_results=3,
        )

        # Extract the closest chunks
        if not results["documents"]:
            raise ValueError(
                "Could not find any matching paragraphs in the Wikipedia page."
            )
        closest_chunks = results["documents"][0]
        return closest_chunks

    def get_prompt(self, response: str, chunks: list[str]) -> str:
        """Generates the prompt to send to the LLM

        Args:
        response (str): LLM response.
        chunks (List[str]): A list of paragraphs of the Wikipedia page.

        Returns:
        prompt (str): The prompt to send to the LLM.
        """

        prompt = """Instructions:
        As an oracle of logic and intelligence, your task is to determine whether the following 'Contexts' support the 'Claim'.
        Please answer the question with just a 'Yes' or a 'No'. Any other text is strictly forbidden.
        You'll be evaluated based on how well you understand the relationship between the contexts and the claim 
        and how well you follow the instructions to answer with a 'Yes' or a 'No'.

        Claim:
        {}

        Contexts:
        {}

        Your Answer:
        
        """.format(
            response, "\n".join(chunks)
        )
        return prompt

    def get_evaluation(self, response: str) -> str:
        """Evaluates the LLM response by re-prompting another LLM.

        Args:
        response (str): LLM response.

        Returns:
        val_response (str): The evaluation response from the LLM.
        """
        # Get the closest matching chunks to the sentence
        closest_chunks = self.get_closest_chunks(response)

        # Get the prompt
        prompt = self.get_prompt(response, closest_chunks)
        print("Prompt:", prompt)

        # Get the LLM response
        messages = [{"content": prompt, "role": "user"}]
        try:
            val_response = completion(model=self.llm_callable, messages=messages)
            val_response = val_response.choices[0].message.content  # type: ignore
            val_response = val_response.strip().lower()
        except Exception as e:
            raise RuntimeError(f"Error getting response from the LLM: {e}") from e

        print("Validation response:", val_response)
        if val_response not in ["yes", "no"]:
            raise ValueError("Received an invalid evaluation response from the LLM.")

        return val_response

    def validate_each_sentence(self, value: str, metadata: Dict) -> ValidationResult:
        """Valudates each sentence in the LLM response."""

        # Split the value into sentences using nltk sentence tokenizer.
        sentences = nltk.sent_tokenize(value)

        unsupported_sentences, supported_sentences = [], []
        for sentence in sentences:
            # Get the LLM response
            val_response = self.get_evaluation(sentence)
            # Check if the LLM response is supported or not
            if val_response == "yes":
                supported_sentences.append(sentence)
            else:
                unsupported_sentences.append(sentence)

        # If there are unsupported sentences, return a FailResult
        if unsupported_sentences:
            unsupported_sentences = "- " + "\n- ".join(unsupported_sentences)
            return FailResult(
                metadata=metadata,
                error_message=(
                    f"None of the following sentences in the response are supported "
                    "by the provided context:"
                    f"\n{unsupported_sentences}"
                ),
                fix_value="\n".join(supported_sentences),
            )
        return PassResult(metadata=metadata)

    def validate_full_text(self, value: str, metadata: Dict) -> ValidationResult:
        """Validates the full text of the LLM response."""

        # Get the LLM response
        val_response = self.get_evaluation(value)

        # If the LLM response is not supported, return a FailResult
        if val_response == "no":
            return FailResult(
                metadata=metadata,
                error_message=(
                    "The response is not supported by the provided context."
                ),
                fix_value="",
            )
        return PassResult(metadata=metadata)

    def validate(self, value: str, metadata: Dict) -> ValidationResult:
        """Validation method for the WikiProvenance validator."""

        # Based on the validation method, validate the LLM response
        if self.validation_method == "sentence":
            return self.validate_each_sentence(value, metadata)
        if self.validation_method == "full":
            return self.validate_full_text(value, metadata)
        raise ValueError(
            f"Validation method {self.validation_method} is not supported."
            "Please use either 'sentence' or 'full'."
        )
