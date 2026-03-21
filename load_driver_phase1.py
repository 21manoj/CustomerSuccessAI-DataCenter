# Shell cheat sheet (run from repo root or load-driver as noted).
#
# Step 0 — optional: copy template and edit customer block (name, domain, admin_email).
#   cp load-driver/manifests/novastar_dc2s.json load-driver/manifests/mountainhigh_dc2s.json
#
# Step 1 — Baseline + register (from load-driver/)
#   python3 cs_pulse_driver.py \
#     --manifest manifests/mountainhigh_dc2s.json \
#     --register \
#     --base-url http://YOUR_HOST \
#     --password "$CS_PULSE_PASSWORD" \
#     --phase baseline \
#     --seed 42
#
# Note customer_id from output, then:
#
# Step 2 — Intervention (same manifest name: mountainhigh_dc2s.json)
#   python3 cs_pulse_driver.py \
#     --manifest manifests/mountainhigh_dc2s.json \
#     --customer-id <ID> \
#     --base-url http://YOUR_HOST \
#     --email admin@your-domain.com \
#     --password "$CS_PULSE_PASSWORD" \
#     --phase intervention \
#     --seed 42

