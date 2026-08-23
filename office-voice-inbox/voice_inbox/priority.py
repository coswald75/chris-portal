"""Priority cues. Exactly these, case-insensitive. Do not invent more.

  - Kyle
  - Kyle note
  - that's a task / thats a task
  - put that on the list
"""

import re

_CUES = re.compile(
    r"\b(?:"
    r"kyle note"
    r"|kyle"
    r"|that[’']?s a task"
    r"|thats a task"
    r"|put that on the list"
    r")\b",
    re.IGNORECASE,
)


def is_priority(text: str) -> bool:
    return bool(_CUES.search(text or ""))
