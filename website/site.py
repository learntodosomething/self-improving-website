"""In-memory representation of a simple static website."""
from pathlib import Path
from typing import Dict


class Website:
    """A static site as a dict of relative file paths -> text content.
    Only .html/.css/.js files are tracked - this prototype does not
    handle images, fonts, or other binary assets.
    """

    SUPPORTED_EXTENSIONS = {".html", ".css", ".js"}

    def __init__(self, files: Dict[str, str]):
        self.files = files

    @classmethod
    def load(cls, folder: str) -> "Website":
        folder_path = Path(folder)
        files: Dict[str, str] = {}
        for path in sorted(folder_path.rglob("*")):
            if path.is_file() and path.suffix in cls.SUPPORTED_EXTENSIONS:
                rel = str(path.relative_to(folder_path)).replace("\\", "/")
                files[rel] = path.read_text(encoding="utf-8")
        if not files:
            raise FileNotFoundError(f"No .html/.css/.js files found in {folder}")
        return cls(files)

    def save(self, folder: str) -> None:
        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        for rel, content in self.files.items():
            target = folder_path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def clone(self) -> "Website":
        return Website(dict(self.files))

    def get_file(self, rel_path: str) -> str:
        return self.files.get(rel_path, "")

    def set_file(self, rel_path: str, content: str) -> None:
        self.files[rel_path] = content

    def combined_source(self) -> str:
        """Single-string representation of the whole site, used for prompting."""
        parts = []
        for rel, content in sorted(self.files.items()):
            parts.append(f"--- {rel} ---\n{content}")
        return "\n\n".join(parts)
