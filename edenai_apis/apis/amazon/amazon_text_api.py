from typing import Sequence
from edenai_apis.features.text.anonymization.anonymization_dataclass import (
    AnonymizationDataClass,
)
from edenai_apis.features.text.keyword_extraction.keyword_extraction_dataclass import (
    InfosKeywordExtractionDataClass,
    KeywordExtractionDataClass,
)
from edenai_apis.features.text.named_entity_recognition.named_entity_recognition_dataclass import (
    InfosNamedEntityRecognitionDataClass,
    NamedEntityRecognitionDataClass,
)
from edenai_apis.features.text.sentiment_analysis.sentiment_analysis_dataclass import (
    SentimentAnalysisDataClass,
)
from edenai_apis.features.text.syntax_analysis.syntax_analysis_dataclass import (
    InfosSyntaxAnalysisDataClass,
    SyntaxAnalysisDataClass,
)
from edenai_apis.features.text.text_interface import TextInterface
from edenai_apis.utils.exception import LanguageException, ProviderException
from edenai_apis.utils.types import ResponseType

from botocore.exceptions import ClientError

from .config import tags


class AmazonTextApi(TextInterface):
    def text__sentiment_analysis(
        self, language: str, text: str
    ) -> ResponseType[SentimentAnalysisDataClass]:
        # Getting response
        try:
            response = self.clients["text"].detect_sentiment(
                Text=text, LanguageCode=language
            )
        except ClientError as exc:
            if "languageCode" in str(exc):
                raise LanguageException(str(exc))

        # Analysing response

        best_sentiment = {
            "general_sentiment": None,
            "general_sentiment_rate": 0,
            "items": [],
        }

        for key in response["SentimentScore"]:
            if key == "Mixed":
                continue

            if (
                best_sentiment["general_sentiment_rate"]
                <= response["SentimentScore"][key]
            ):
                best_sentiment["general_sentiment"] = key
                best_sentiment["general_sentiment_rate"] = response["SentimentScore"][
                    key
                ]

        standarize = SentimentAnalysisDataClass(
            general_sentiment=best_sentiment["general_sentiment"],
            general_sentiment_rate=best_sentiment["general_sentiment_rate"],
            items=[],
        )

        return ResponseType[SentimentAnalysisDataClass](
            original_response=response, standardized_response=standarize
        )

    def text__keyword_extraction(
        self, language: str, text: str
    ) -> ResponseType[KeywordExtractionDataClass]:
        # Getting response
        try:
            response = self.clients["text"].detect_key_phrases(
                Text=text, LanguageCode=language
            )
        except ClientError as exc:
            if "languageCode" in str(exc):
                raise LanguageException(str(exc))

        # Analysing response
        items: Sequence[InfosKeywordExtractionDataClass] = []
        for key_phrase in response["KeyPhrases"]:
            items.append(
                InfosKeywordExtractionDataClass(
                    keyword=key_phrase["Text"], importance=key_phrase["Score"]
                )
            )

        standardized_response = KeywordExtractionDataClass(items=items)

        return ResponseType[KeywordExtractionDataClass](
            original_response=response, standardized_response=standardized_response
        )

    def text__named_entity_recognition(
        self, language: str, text: str
    ) -> ResponseType[NamedEntityRecognitionDataClass]:
        # Getting response
        try:
            response = self.clients["text"].detect_entities(
                Text=text, LanguageCode=language
            )
        except ClientError as exc:
            if "languageCode" in str(exc):
                raise LanguageException(str(exc)) from exc
            else:
                raise ProviderException(str(exc)) from exc

        items: Sequence[InfosNamedEntityRecognitionDataClass] = []
        for ent in response["Entities"]:

            items.append(
                InfosNamedEntityRecognitionDataClass(
                    entity=ent["Text"],
                    importance=ent["Score"],
                    category=ent["Type"],
                )
            )

        standardized = NamedEntityRecognitionDataClass(items=items)

        return ResponseType[NamedEntityRecognitionDataClass](
            original_response=response, standardized_response=standardized
        )

    def text__syntax_analysis(
        self, language: str, text: str
    ) -> ResponseType[SyntaxAnalysisDataClass]:

        # Getting response
        try:
            response = self.clients["text"].detect_syntax(
                Text=text, LanguageCode=language
            )
        except ClientError as exc:
            if "languageCode" in str(exc):
                raise LanguageException(str(exc))

        # Create output TextSyntaxAnalysis object

        items: Sequence[InfosSyntaxAnalysisDataClass] = []

        # Analysing response
        #
        # Getting syntax detected of word and its score of confidence
        for ent in response["SyntaxTokens"]:
            tag = tags[ent["PartOfSpeech"]["Tag"]]
            items.append(
                InfosSyntaxAnalysisDataClass(
                    word=ent["Text"],
                    importance=ent["PartOfSpeech"]["Score"],
                    tag=tag,
                )
            )

        standardized_response = SyntaxAnalysisDataClass(items=items)

        return ResponseType[SyntaxAnalysisDataClass](
            original_response=response, standardized_response=standardized_response
        )

    def text__anonymization(
        self, text: str, language: str
    ) -> ResponseType[AnonymizationDataClass]:
        try:
            res = self.clients["text"].detect_pii_entities(
                Text=text, LanguageCode=language
            )
        except Exception as exc:
            raise ProviderException(exc) from exc

        last_end = 0
        new_text = ""
        for entity in res["Entities"]:
            new_text += text[last_end : entity["BeginOffset"]] + f"<{entity['Type']}>"
            last_end = entity["EndOffset"]
        standardized_response = AnonymizationDataClass(result=new_text)
        return ResponseType(
            original_response=res, standardized_response=standardized_response
        )
