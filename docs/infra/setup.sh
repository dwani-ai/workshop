#!bin/bash

mkdir dwani_workshop_infra

cd dwani_workshop_infra

git clone https://github.com/dwani-ai/llm-indic-server
git clone https://github.com/dwani-ai/indic-translate-server
git clone https://github.com/dwani-ai/asr-indic-server
git clone https://github.com/dwani-ai/tts-indic-server
git clone https://github.com/dwani-ai/docs-indic-server
git clone https://github.com/dwani-ai/dwani-server


cd llm-indic-server
python3.10 -m venv venv
source venv/bin/actiave
pip install -r requirements.txt

deactivate

cd indic-translate-server
python3.10 -m venv venv
source venv/bin/actiave
pip install -r requirements.txt

deactivate

cd asr-indic-server
python3.10 -m venv venv
source venv/bin/actiave
pip install -r requirements.txt

deactivate

cd tts-indic-server
python3.10 -m venv venv
source venv/bin/actiave
pip install -r requirements.txt

deactivate

cd docs-indic-server
python3.10 -m venv venv
source venv/bin/actiave
pip install -r requirements.txt

deactivate

cd dwani-server
python3.10 -m venv venv
source venv/bin/actiave
pip install -r requirements.txt
