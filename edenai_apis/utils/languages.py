import re
from collections import defaultdict
from importlib import import_module
from typing import List, Optional, Sequence

import pycountry
from edenai_apis.loaders.data_loader import ProviderDataEnum
from edenai_apis.loaders.loaders import load_provider
from langcodes import Language, closest_supported_match



AUTO_DETECT = "auto-detect"
AUTO_DETECT_NAME = "Auto detection"

class LanguageErrorMessage:
    LANGUAGE_REQUIRED = lambda input_lang: (
        f"This provider doesn't auto-detect languages, "
        f"please provide a valid {input_lang}"
    )
    LANGUAGE_NOT_SUPPORTED = lambda lang, input_lang: (
        f"Provider does not support selected {input_lang}: `{lang}`"
    )

    LANGUAGE_GENERIQUE_REQUESTED = lambda lang, suggested_lang, input_lang: (
        f"Provider does not support selected {input_lang}:'{lang}'. Please try"
        f" a more general language: '{suggested_lang}'"
    )

    LANGUAGE_SYNTAX_ERROR = lambda lang: (
        f"Invalid language format for: '{lang}'."
    )


def check_language_format(iso_code: str) -> bool:
    """Checks if language code name is formatted correctly (lang-extlang-Script-Reg)"""
    if iso_code is None:
        return None
    return bool(
        re.fullmatch(
            r"^[a-z]{2,3}(-[a-z]{2,3})?(-[A-Z][a-z]{3})?(-([A-Z]{2,3}|\d{3}))?",
            iso_code,
        )
    )


def convert_three_two_letters(iso_code: str) -> Optional[str]:
    """Converts an iso639-3 language code to an iso639-2 language code if possible"""
    if iso_code is None:
        return None
    if "-" in iso_code and len(iso_code.split("-")[0]) == 3:
        return str(Language.get(iso_code))
    if len(iso_code) != 3:
        return iso_code
    language = pycountry.languages.get(alpha_3=iso_code)
    if not language:  # can not find language in pycountry from it's alpha_3 code
        return str(Language.get(iso_code))
    return language.alpha_2 if hasattr(language, "alpha_2") else language.alpha_3


def load_language_constraints(provider_name: str, feature: str, subfeature: str) -> list:
    """Loads the list of languages supported by
    the provider for a couple of (feature, subfeature)"""
    info = load_provider(
        ProviderDataEnum.PROVIDER_INFO,
        provider_name=provider_name,
        feature=feature,
        subfeature=subfeature
    )
    default = defaultdict(lambda: None)
    languages = info.get("constraints", default).get("languages", [])
    if info.get("constraints", default).get("allow_null_language"):
        languages.append(AUTO_DETECT)
    return languages


def expand_languages_for_user(list_languages: list) -> list:
    """Returns a list that extends the input list of languages (list_language)
    with formatted language tags and iso639-3 language codes"""
    appended_list = []
    for language in list_languages:
        if language == AUTO_DETECT:
            appended_list.append(language)
            continue
        if "-" in language:
            if (
                "Unknown language"
                not in Language.get(language.split("-")[0]).display_name()
            ):
                appended_list.append(convert_three_two_letters(language.split("-")[0]))
        appended_list.append(convert_three_two_letters(language))
    return appended_list


def load_standardized_language(feature: str, subfeature: str, providers: Optional[List[str]]):
    """Displays a standardized list of languages for a list of providers
    for the pair (feature, subfeature)"""

    if providers is None:
        interface = import_module('edenai_apis.interface')
        providers = interface.list_providers(feature, subfeature)

    result = []
    for provider in providers:
        list_languages = expand_languages_for_user(
            load_language_constraints(provider, feature, subfeature)
        )
        result = list(set(list_languages + result))
    return result


def format_language_name(language_name: str, isocode: str) -> str:
    """Formats language name by removing 'language'
    if this latter in Unknown or also removing 'region' if it's Unknown"""
    if "Unknown language" in language_name:
        formatted = re.search(r"\([a-zA-Z\s]*\)", language_name)
        return (
            f"Region: {formatted.group().split(')')[0].split('(')[1].strip()}"
            if formatted is not None
            else isocode
        )
    if "Unknown Region" in language_name:
        formatted = re.search(r"[a-zA-Z\s]*\(", language_name)
        return formatted.group().split("(")[0].strip()
    return language_name


def get_language_name_from_code(isocode: str) -> str:
    """Returns the language name from the isocode"""
    if isocode is None:
        return ""
    if isocode == AUTO_DETECT:
        return AUTO_DETECT_NAME
    if "-" not in isocode:
        language = (
            pycountry.languages.get(alpha_2=isocode)
            if len(isocode) == 2
            else pycountry.languages.get(alpha_3=isocode)
        )
        if not language and not isocode:
            return ""
        output = Language.get(isocode).display_name() if not language else language.name
    else:
        language = Language.get(isocode)
        output = language.display_name()
    return format_language_name(output, isocode)

def get_code_from_language_name(name: str) -> str:
    """Returns the iso639-2 from the language name"""
    try:
        if not name:
            return 'Unknow'
        output = Language.find(name=name)
    except LookupError:
        return 'Unknow'
    return output.__str__()

def has_language_contrains_script(iso_code: str, selected_code_language: str) -> bool:
    ## To be able to handle zh (chinese) constraints
    if Language.get(iso_code).script:
        if Language.get(iso_code).language == Language.get(selected_code_language).language:
            return True
    return False


def compare_language_and_region_code(iso_code: str, selected_code_language: str) -> bool:
    return Language.get(iso_code).language == Language.get(selected_code_language).language and \
                Language.get(iso_code).territory == Language.get(selected_code_language).territory 


def provide_appropriate_language(iso_code: str, provider_name: str, feature: str, subfeature: str):
    if not check_language_format(iso_code):
        raise SyntaxError(f"Language code '{iso_code}' badly formatted")

    list_languages: Sequence[str] = load_language_constraints(provider_name, feature, subfeature)

    # Sometimes closest_supported_match raise a RuntimeError,
    # so we need a while True for catch this error and retry until function works
    while True:
        try:
            selected_code_language = closest_supported_match(iso_code, list_languages)
            break
        except RuntimeError:
            pass

    if '-' in iso_code and selected_code_language:
        if has_language_contrains_script(iso_code, selected_code_language):
            return selected_code_language
        if (compare_language_and_region_code(iso_code, selected_code_language)):
            return selected_code_language
        return None

    return selected_code_language
