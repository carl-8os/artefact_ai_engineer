"""Resolve the original challenge filenames without depending on their prefixes."""
from pathlib import Path


def resolve_csv(directory: Path, name: str) -> Path:
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f'CSV directory not found: {directory}')
    matches = [p for p in directory.iterdir() if p.is_file() and
               (p.name.casefold() == f'{name}.csv' or p.name.casefold().endswith(f' - {name}.csv'))]
    if len(matches) != 1:
        raise FileNotFoundError(f'Expected exactly one {name}.csv (or * - {name}.csv) in {directory}; found {len(matches)}')
    return matches[0]
