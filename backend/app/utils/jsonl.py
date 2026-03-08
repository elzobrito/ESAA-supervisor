import json
from typing import Any, List


def _parse_json_objects(line: str) -> List[Any]:
    line = line.lstrip("\ufeff")
    decoder = json.JSONDecoder()
    items: List[Any] = []
    index = 0
    length = len(line)

    while index < length:
        while index < length and line[index].isspace():
            index += 1
        if index >= length:
            break
        item, index = decoder.raw_decode(line, index)
        items.append(item)

    return items


def read_jsonl(file_path: str) -> List[Any]:
    data: List[Any] = []
    with open(file_path, "rb") as f:
        for raw_line in f:
            try:
                line = raw_line.decode("utf-8")
            except UnicodeDecodeError:
                line = raw_line.decode("utf-8", errors="replace")
            line = line.strip().lstrip("\ufeff")
            if not line:
                continue
            try:
                data.extend(_parse_json_objects(line))
            except json.JSONDecodeError:
                continue
    return data


def append_jsonl(file_path: str, item: Any):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
