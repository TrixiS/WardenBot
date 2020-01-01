

def multi_replace(string: str, tokens: list, to_replace: str) -> str:
    for token in tokens:
        string = string.replace(token, to_replace)
    
    return string


def markdown(string: str, tag: str) -> str:
    return f"{tag}{string}{tag}"


def join_or_default(iterable, separator: str, default: str="") -> str:
    result = separator.join(iterable)

    return result or default


def collect_attributes(iterable, *args) -> str:
    result = []

    for item in iterable:
        result.append(str(getattr(item, *args)))

    return result

