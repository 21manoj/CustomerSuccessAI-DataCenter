#!/usr/bin/env python3
"""
Generate Data Quality report and write it to instance/dq_reports/.
Intended to be run on a schedule (e.g., 1:00 AM) via cron or a task runner.
"""

import os
import json
import datetime
from pathlib import Path

from app_v3_minimal import app
from data_quality_api import get_data_quality_report


def main():
    with app.app_context():
        resp = get_data_quality_report()
        report = resp.get_json()

        # Write to instance/dq_reports directory
        basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        instance_dir = os.path.abspath(os.path.join(basedir, '..', 'instance', 'dq_reports'))
        Path(instance_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        outfile = os.path.join(instance_dir, f'dq_report_{timestamp}.json')
        with open(outfile, 'w') as f:
            json.dump(report, f, indent=2)

        print(f'✅ Data Quality report written to {outfile}')


if __name__ == '__main__':
    main()


