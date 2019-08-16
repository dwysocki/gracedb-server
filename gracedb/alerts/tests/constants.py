import re


# Constants for use in various tests
DEFAULT_FAR_T = 1  # Hz
DEFAULT_LABELS = ['L1', 'L2']
LABEL_QUERY_PARSER = re.compile(r'([a-zA-Z0-9]+)')
DEFAULT_LABEL_QUERY = {'query': 'L3 & L4'}
DEFAULT_LABEL_QUERY['labels'] = LABEL_QUERY_PARSER.findall(
    DEFAULT_LABEL_QUERY['query']
)
LABEL_QUERY2 = 'L5 & L6 & ~L7'
RANDOM_LABEL = 'L12345'
DEFAULT_GROUP = 'Group1'
DEFAULT_PIPELINE = 'Pipeline1'
DEFAULT_SEARCH = 'Search1'
