#!/bin/sh

python -m build && python -m twine upload -r safe-exit dist/*