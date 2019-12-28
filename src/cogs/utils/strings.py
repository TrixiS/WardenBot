

def multi_replace(string: str, tokens: list, to_replace: str) -> str:
    for token in tokens:
        string = string.replace(token, to_replace)
    
    return string


def markdown(string: str, tag: str) -> str:
    return f"{tag}{string}{tag}"
    