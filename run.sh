export $(cat .env | xargs)

source .venv/bin/activate && python armor.py "$@"