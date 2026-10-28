"""A document the AI saved is shown to the user as a card, so a link to it in the AI's text only repeats the card."""

import re
from urllib.parse import quote


def link_to_document(name: str) -> re.Pattern:
	"""A Markdown link to a Desk or Raven page of the document `name`."""
	return re.compile(rf"\[[^\]]*\]\([^)]*/(?:app|desk)/[^)]*(?:{re.escape(name)}|{re.escape(quote(name))})[^)]*\)")


def without_card_links(answer: str, documents: list[dict]) -> str:
	"""The answer without Markdown links to the documents that are shown as cards; a line the link leaves empty goes too."""
	for document in documents:
		pattern = link_to_document(document["docname"])
		lines = []
		for line in answer.split("\n"):
			cleaned = pattern.sub("", line)
			if cleaned.strip() or not pattern.search(line):
				lines.append(cleaned)
		answer = "\n".join(lines)
	return answer.strip()
