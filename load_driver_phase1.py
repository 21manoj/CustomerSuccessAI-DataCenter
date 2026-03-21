# Shell cheat sheet (run from repo root or load-driver as noted).
#
# EC2 deploy (primary app): http://3.93.17.185  — Platform B (extra capacity): http://3.93.17.185:9080
#
# Step 0 — optional: copy template and edit customer block (name, domain, admin_email).
#   cp load-driver/manifests/novastar_dc2s.json load-driver/manifests/mountainhigh_dc2s.json
#
# Step 1 — Baseline + register (from load-driver/)
#   python3 cs_pulse_driver.py \
#     --manifest manifests/mountainhigh_dc2s.json \
#     --register \
#     --base-url http://3.93.17.185 \
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
#     --base-url http://3.93.17.185 \
#     --email admin@your-domain.com \
#     --password "$CS_PULSE_PASSWORD" \
#     --phase intervention \
#     --seed 42
#
# Mount Fuji (rich manifest, same as Mount-Everest template):
#   --manifest manifests/Mount-Fuji_dc2.json --register --phase baseline  (note customer_id)
#   --manifest manifests/Mount-Fuji_dc2.json -c <ID> --email admin@mount-fuji-dc.com --phase intervention

