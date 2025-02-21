from enum import Enum
from io import BufferedReader
import json
from typing import List, Optional

import requests
from edenai_apis.features import (
    ProviderInterface,
    TextInterface,
    TranslationInterface,
    AudioInterface
)
from edenai_apis.features.audio import (
    SpeechToTextAsyncDataClass,
    SpeechDiarizationEntry,
    SpeechDiarization
)
from edenai_apis.features.text import (
    AnonymizationDataClass,
    KeywordExtractionDataClass,
    NamedEntityRecognitionDataClass,
    InfosNamedEntityRecognitionDataClass,
    InfosKeywordExtractionDataClass,
    SentimentAnalysisDataClass,
    SummarizeDataClass,
    SentimentEnum,
)
from edenai_apis.features.text.sentiment_analysis.sentiment_analysis_dataclass import SegmentSentimentAnalysisDataClass
from edenai_apis.features.translation import (
    LanguageDetectionDataClass,
)
from edenai_apis.features.translation.language_detection import (
    InfosLanguageDetectionDataClass,
)
from edenai_apis.loaders.data_loader import ProviderDataEnum
from edenai_apis.loaders.loaders import load_provider
from edenai_apis.utils.exception import ProviderException
from edenai_apis.utils.types import (
    AsyncBaseResponseType,
    AsyncLaunchJobResponseType,
    AsyncPendingResponseType,
    AsyncResponseType,
    ResponseType
)

from edenai_apis.utils.languages import get_code_from_language_name

class StatusEnum(Enum):
    SUCCESS = 'COMPLETED'
    RUNNING = 'RUNNING'
    FAILED = 'FAILED'

class OneaiApi(
    ProviderInterface,
    TextInterface,
    TranslationInterface,
    AudioInterface
):
    provider_name = 'oneai'

    def __init__(self) -> None:
        self.api_settings = load_provider(ProviderDataEnum.KEY, self.provider_name)
        self.api_key = self.api_settings['api_key']
        self.url = self.api_settings['url']
        self.header = {
            "api-key": self.api_key,
            "accept": "application/json",
            "Content-Type": "application/json",
        }

    
    def text__anonymization(self, text: str, language: str) -> ResponseType[AnonymizationDataClass]:
        data = json.dumps({
            "input": text,
            "steps": [
                {
                    "skill": "anonymize"
                }
            ]
        })

        response = requests.post(url=self.url, headers=self.header, data=data)
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)
        
        standardized_response = AnonymizationDataClass(result=original_response['output'][0]['text'])

        return ResponseType[AnonymizationDataClass](
            original_response=original_response,
            standardized_response=standardized_response
        )


    def text__keyword_extraction(self, language: str, text: str) -> ResponseType[KeywordExtractionDataClass]:
        data = json.dumps({
            "input": text,
            "steps": [
                {
                    "skill": "keywords"
                }
            ]
        })

        response = requests.post(url=self.url, headers=self.header, data=data)
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)

        items = []
        for item in original_response['output'][0]['labels']:
            items.append(InfosKeywordExtractionDataClass(keyword=item['span_text'], importance=round(item['value'], 2)))

        standardized_response = KeywordExtractionDataClass(items=items)

        return ResponseType[KeywordExtractionDataClass](
            original_response=original_response,
            standardized_response=standardized_response
        )

    def text__named_entity_recognition(self, language: str, text: str) -> ResponseType[NamedEntityRecognitionDataClass]:
        data = json.dumps({
            "input": text,
            "steps": [
                {
                    "skill": "names"
                }
            ]
        })

        response = requests.post(url=self.url, headers=self.header, data=data)
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)

        items = []
        for item in original_response['output'][0]['labels']:
            entity = item['value']
            category = item['name']
            if category == 'GEO':
                category = 'LOCATION'
            items.append(InfosNamedEntityRecognitionDataClass(entity=entity, category=category))

        standardized_response = NamedEntityRecognitionDataClass(items=items)

        return ResponseType[NamedEntityRecognitionDataClass](
            original_response=original_response,
            standardized_response=standardized_response
        )

    def text__sentiment_analysis(self, language: str, text: str) -> ResponseType[SentimentAnalysisDataClass]:
        data = json.dumps({
            "input": text,
            "steps": [
                {
                    "skill": "sentiments"
                }
            ]
        })

        response = requests.post(url=self.url, headers=self.header, data=data)
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)

        items = []
        general_sentiment = 0
        for item in original_response['output'][0]['labels']:
            segment = item['span_text']
            sentiment = SentimentEnum.NEGATIVE if item['value'] == 'NEG' else SentimentEnum.POSITIVE
            general_sentiment += 1 if sentiment == SentimentEnum.POSITIVE else -1
            items.append(SegmentSentimentAnalysisDataClass(
                segment=segment,
                sentiment=sentiment.value
            ))

        general_sentiment_text = SentimentEnum.NEUTRAL
        if general_sentiment < 0:
            general_sentiment_text = SentimentEnum.NEGATIVE
        elif general_sentiment > 0:
            general_sentiment = SentimentEnum.POSITIVE

        standardized_response = SentimentAnalysisDataClass(
            general_sentiment=general_sentiment_text.value,
            items=items
        )

        return ResponseType[SentimentAnalysisDataClass](
            original_response=original_response,
            standardized_response=standardized_response
        )

    def text__summarize(self, text: str, output_sentences: int, language: str, model: Optional[str]) -> ResponseType[SummarizeDataClass]:
        data = json.dumps({
            "input": text,
            "steps": [
                {
                    "skill": "summarize"
                }
            ]
        })

        response = requests.post(url=self.url, headers=self.header, data=data)
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)

        text = original_response['output'][0]['text']

        standardized_response = SummarizeDataClass(result=text)

        return ResponseType[SummarizeDataClass](
            original_response=original_response,
            standardized_response=standardized_response
        )

    def translation__language_detection(self, text) -> ResponseType[LanguageDetectionDataClass]:
        data = json.dumps({
            "input": text,
            "steps": [
                {
                    "skill": "detect-language"
                }
            ],
            "multilingual": True
        })

        response = requests.post(url=self.url, headers=self.header, data=data)
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)

        items = []
        for item in original_response['output'][0]['labels']:
            items.append(InfosLanguageDetectionDataClass(
                language=get_code_from_language_name(name=item['value']),
                display_name=item['value']
            ))

        return ResponseType[LanguageDetectionDataClass](
            original_response=original_response,
            standardized_response=LanguageDetectionDataClass(items=items)
        )



    def audio__speech_to_text_async__launch_job(
        self, 
        file: str,
        language: str, 
        speakers: int, 
        profanity_filter: bool, 
        vocabulary: Optional[List[str]],
        audio_attributes: tuple,
        file_url: str = "",
        ) -> AsyncLaunchJobResponseType:

        export_format, channels, frame_rate = audio_attributes

        data = {
            "input_type": 'conversation',
            "content_type": "audio/"+export_format,
            "steps": [
                {
                    "skill": "transcribe",
                    "params": {
                        "speaker_detection": True,
                        "engine": "whisper"
                    }
                }
            ],
            "multilingual": True
        }

        file_ = open(file, "rb")
        response = requests.post(url=f"{self.url}/async/file?pipeline={json.dumps(data)}", headers=self.header, data=file_.read())
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)

        return AsyncLaunchJobResponseType(
            provider_job_id=original_response['task_id']
        )


    def audio__speech_to_text_async__get_job_result(self, provider_job_id: str) -> AsyncBaseResponseType[SpeechToTextAsyncDataClass]:
        response = requests.get(url=f"{self.url}/async/tasks/{provider_job_id}", headers=self.header)

        original_response = response.json()

        if response.status_code == 200:
            if original_response['status'] == StatusEnum.SUCCESS.value:
                final_text = ""
                phrase = original_response['result']['input_text'].split('\n\n')
                for item in phrase:
                    if item != '':
                        *options, text = item.split('\n')
                        final_text += f"{text} "
                
                diarization_entries = []
                speakers = set()
                words_info = original_response["result"]["output"][0]["labels"]

                for word_info in words_info:
                    speakers.add(word_info["speaker"])
                    diarization_entries.append(
                        SpeechDiarizationEntry(
                            segment= word_info["span_text"],
                            start_time= word_info["timestamp"],
                            end_time= word_info["timestamp_end"],
                            speaker= int(word_info["speaker"].split("speaker")[1])
                        )
                    )
                diarization = SpeechDiarization(total_speakers=len(speakers), entries= diarization_entries)
                standardized_response=SpeechToTextAsyncDataClass(text=final_text.strip(),
                        diarization= diarization)
                return AsyncResponseType[SpeechToTextAsyncDataClass](
                    original_response=original_response,
                    standardized_response=standardized_response,
                    provider_job_id=provider_job_id
                )
            elif original_response['status'] == StatusEnum.RUNNING.value:
                return AsyncPendingResponseType[SpeechToTextAsyncDataClass](provider_job_id=provider_job_id)
            else:
                raise ProviderException(original_response)
        else:
            raise ProviderException(original_response)
