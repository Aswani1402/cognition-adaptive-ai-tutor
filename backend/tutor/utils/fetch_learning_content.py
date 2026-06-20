# tutor/utils/fetch_learning_content.py

from tutor.utils.concept_mapper import map_system_to_content
from tutor.utils.content_fetcher import fetch_concept_resource


def get_learning_content(system_concept_id):
    content_id, domain = map_system_to_content(system_concept_id)

    if not content_id:
        return None

    resource = fetch_concept_resource(domain, content_id)

    return resource