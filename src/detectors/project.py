"""Technology and safe check command detection."""
from __future__ import annotations

from pathlib import Path

MARKERS = {
    "Python": ["pyproject.toml", "requirements.txt", "setup.py"],
    "Django": ["manage.py"],
    "Node.js": ["package.json"],
    "TypeScript": ["tsconfig.json"],
    "Laravel": ["artisan"],
    "PHP": ["composer.json"],
    "C# / ASP.NET Core": ["*.csproj", "*.sln"],
    "React": ["src/App.tsx", "src/App.jsx"],
    "Next.js": ["next.config.js", "next.config.mjs", "next.config.ts"],
}


def detect_technology(root: Path) -> list[str]:
    found = []
    for name, patterns in MARKERS.items():
        matches = []
        for pattern in patterns:
            matches.extend(root.glob(pattern) if "*" in pattern else [root / pattern])
        if any(path.exists() for path in matches):
            found.append(name)
    return found or ["HTML/CSS or unknown"]


def check_commands(root: Path, technologies: list[str]) -> list[list[str]]:
    if (root / "package.json").exists():
        return [["npm", "test", "--if-present"], ["npm", "run", "build", "--if-present"]]
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return [["python", "-m", "compileall", "-q", "."]]
    if (root / "composer.json").exists():
        return [["composer", "validate", "--no-check-publish"]]
    return []
