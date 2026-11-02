"""Zero-dependency launcher for notebook use (no pip install required)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from music_store.presentation.cli import main
from music_store.presentation.web import serve

if __name__ == '__main__':
    if '--web' in sys.argv:
        sys.argv.remove('--web')
        import argparse
        parser = argparse.ArgumentParser(description='Local web chat')
        parser.add_argument('--data', type=Path, default=Path('data'))
        parser.add_argument('--port', type=int, default=8765)
        args = parser.parse_args()
        serve(args.data, port=args.port)
    else:
        main()
