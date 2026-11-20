"""Read the original OpenStep project without rewriting existing objects.

This is deliberately a structural reader for source-preservation checks, not an
Xcode build substitute. The Apple gate still asks Xcode to build the real target.
"""
import json
import re


def require(value, message):
    if not value:
        raise ValueError(message)


TOKEN = re.compile(r'\s+|//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}()=;,]|[^\s{}()=;,]+', re.S)


def loads(text):
    tokens = []
    position = 0
    for match in TOKEN.finditer(text):
        require(match.start() == position, "Unsupported project syntax")
        position = match.end()
        token = match.group()
        if token.isspace() or token.startswith(("//", "/*")):
            continue
        tokens.append(token)
    require(position == len(text), "Unparsed project tail")
    cursor = 0

    def value():
        nonlocal cursor
        require(cursor < len(tokens), "Truncated project value")
        token = tokens[cursor]
        cursor += 1
        if token == "{":
            result = {}
            while cursor < len(tokens) and tokens[cursor] != "}":
                key = value()
                require(isinstance(key, str) and key not in result, "Duplicate project key")
                require(cursor < len(tokens) and tokens[cursor] == "=", "Missing project equals")
                cursor += 1
                result[key] = value()
                require(cursor < len(tokens) and tokens[cursor] == ";", "Missing project semicolon")
                cursor += 1
            require(cursor < len(tokens), "Unclosed project dictionary")
            cursor += 1
            return result
        if token == "(":
            result = []
            while cursor < len(tokens) and tokens[cursor] != ")":
                result.append(value())
                if cursor < len(tokens) and tokens[cursor] == ",":
                    cursor += 1
                else:
                    require(cursor < len(tokens) and tokens[cursor] == ")", "Missing project comma")
            require(cursor < len(tokens), "Unclosed project array")
            cursor += 1
            return result
        require(token not in "{}()=;,", "Unexpected project punctuation")
        return json.loads(token) if token.startswith('"') else token

    result = value()
    require(cursor == len(tokens) and isinstance(result, dict), "Trailing or non-dictionary project")
    return result


def render(value, indent=0):
    """Serialize new objects only; never round-trip the original whole project."""
    if isinstance(value, dict):
        return "{\n" + "".join("\t" * (indent + 1) + json.dumps(key) + " = "
                                + render(item, indent + 1) + ";\n"
                                for key, item in value.items()) + "\t" * indent + "}"
    if isinstance(value, list):
        return "(\n" + "".join("\t" * (indent + 1) + render(item, indent + 1) + ",\n"
                                for item in value) + "\t" * indent + ")"
    require(isinstance(value, str), "Project values must remain original string atoms")
    return json.dumps(value, ensure_ascii=False)


def object_text(text, identifier):
    pattern = re.compile(r"(?m)^\t\t" + re.escape(identifier) + r"(?: /\*[^\n]*?\*/)? = \{")
    matches = list(pattern.finditer(text))
    require(len(matches) == 1, "Project object is missing or duplicated: " + identifier)
    start = matches[0].start()
    cursor = matches[0].end() - 1
    depth = 0
    quoted = False
    escaped = False
    while cursor < len(text):
        char = text[cursor]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                require(text[cursor:cursor + 3] == "};\n", "Unexpected project object end")
                return text[start:cursor + 3]
        cursor += 1
    raise ValueError("Unclosed project object: " + identifier)


def append_array(text, identifier, key, item, label):
    original = object_text(text, identifier)
    marker = "\t\t\t" + key + " = (\n"
    require(original.count(marker) == 1, "Expected one original target array")
    start = original.index(marker) + len(marker)
    end = original.index("\t\t\t);", start)
    changed = original[:end] + "\t\t\t\t" + item + " /* " + label + " */,\n" + original[end:]
    return text.replace(original, changed, 1)
