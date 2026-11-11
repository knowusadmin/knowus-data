#!/bin/bash
# KnowUS post-build: re-apply contacts + Husted fix + ctBox footer + repo policy/EO-hist. Idempotent. usage: postbuild.sh SITE_DIR
set -e
S=$1; R=/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/repo; H=/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers
timeout -k 5 120 python3 $R/scripts/contacts/apply_contacts.py $S $R/data/contacts
timeout -k 5 30 python3 $H/ghfix1111/husted_patch.py $S/data.js
timeout -k 5 30 python3 $H/nation47/ctbox_patch.py $S/app.js
cp $R/data/sources-policy.json $S/data/sources-policy.json
cp $R/data/ai-summaries/EO-hist.json $S/data/ai-summaries/EO-hist.json
echo POSTBUILD_OK
