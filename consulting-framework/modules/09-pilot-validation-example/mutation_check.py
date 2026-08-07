"""Mutation harness: re-introduce each defect the corrected implementation
fixed, and confirm the test suite actually catches it.  A SURVIVED row means
a test is decorative.  Run: python3 mutation_check.py"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "ingestion.py")
TST = os.path.join(HERE, "test_ingestion.py")

MUTS = [
    ("M1  revert UTC fix in has_new_data",
     'mtime = datetime.fromtimestamp(os.stat(str(f)).st_mtime,\n'
     '                                           tz=timezone.utc)',
     'mtime = datetime.fromtimestamp(os.stat(str(f)).st_mtime)'),
    ("M1b revert utc_has_new_data to naive local",
     'mtime = datetime.fromtimestamp(mtime_epoch, tz=timezone.utc)\n'
     '    return mtime > as_utc(last_ingested_at)',
     'mtime = (datetime.fromtimestamp(mtime_epoch, tz=timezone.utc)\n'
     '             + timedelta(hours=-7)).replace(tzinfo=None)\n'
     '    return mtime > last_ingested_at.replace(tzinfo=None)'),
    ("M2  rows_rejected back to len(errors)",
     'return UploadResult(file_type, len(accepted), rejected_rows,\n'
     '                                errors, None, True)',
     'return UploadResult(file_type, len(accepted), len(errors),\n'
     '                                errors, None, True)'),
    ("M3  freshness measured from last_ingested_at",
     'last = as_utc(_parse_ts(state["last_processed_at"]))',
     'last = as_utc(_parse_ts(state["last_ingested_at"]))'),
    ("M4  drop the Skip mechanism",
     'if isinstance(outcome, Skip):\n'
     '                results.append(self._skip(stage.name, outcome.reason))\n'
     '            else:',
     'if False:\n                pass\n            else:'),
    ("M5  persist() returns None again",
     'return self.store_raw(customer_id, file_type, deduped)',
     'return None'),
    ("M6  drop NULL sentinel in natural_key",
     'key.append(NULL_SENTINEL if v in (None, "") else v)',
     'key.append(v)'),
    ("M7  drop referential validation",
     'row_errors = row_errors + self.validate_referential(\n'
     '                customer_id, file_type, row, i)',
     'row_errors = row_errors'),
    ("M8  allow a blank skip reason",
     'if not reason or not str(reason).strip():\n'
     '            raise ValueError("stage %r skipped with no reason" % name)',
     'pass'),
    ("M9  report success even when a stage failed",
     'status = "partial" if any(r.status == "failed" for r in results) \\\n'
     '            else "success"',
     'status = "success"'),
    ("M10 critical stage no longer aborts",
     'if stage.critical:\n'
     '                    timings[stage.name] = monotonic() - t0\n'
     '                    aborted = True\n'
     '                    break',
     'if False:\n                    pass'),
    ("M11 drop the freshness_check reason stage",
     'results = [StageResult("freshness_check", "completed", reason, None)]',
     'results = []'),
    ("M12 dry-run persists anyway",
     'if validate_only:\n'
     '            # dry-run persists nothing, creates no accounts, moves no clock\n'
     '            return UploadResult(file_type, len(accepted), rejected_rows,\n'
     '                                errors, None, True)',
     'if validate_only:\n'
     '            self.persist(customer_id, file_type, accepted)\n'
     '            return UploadResult(file_type, len(accepted), rejected_rows,\n'
     '                                errors, None, True)'),
    ("M13 drop new_upload (API-payload) freshness",
     'if ingested > last:\n            return True, "new_upload"',
     'if False:\n            pass'),
    ("M14 upsert -> bare INSERT",
     'sql = "INSERT INTO %s (%s) VALUES (%s) ON CONFLICT(%s) DO UPDATE SET %s" % (\n'
     '            file_type, ",".join(all_cols), ",".join(["?"] * len(all_cols)),\n'
     '            conflict, set_clause)',
     'sql = "INSERT INTO %s (%s) VALUES (%s)" % (\n'
     '            file_type, ",".join(all_cols), ",".join(["?"] * len(all_cols)))'),
    ("M15 natural_key ignores optional cols (row[c])",
     'v = row.get(c)\n            key.append(NULL_SENTINEL if v in (None, "") else v)',
     'key.append(row[c])'),
]


def main():
    base = open(SRC).read()
    survived = 0
    for name, old, new in MUTS:
        if old not in base:
            print("%-45s SKIP (anchor not found)" % name)
            continue
        d = tempfile.mkdtemp(prefix="mut-")
        with open(os.path.join(d, "ingestion.py"), "w") as fh:
            fh.write(base.replace(old, new, 1))
        shutil.copy(TST, d)
        r = subprocess.run([sys.executable, "-m", "unittest", "test_ingestion"],
                           cwd=d, capture_output=True, text=True)
        n = len(re.findall(r"^(?:FAIL|ERROR):", r.stderr, re.M))
        ok = r.returncode != 0
        survived += (not ok)
        print("%-45s %-16s (%d tests bit)"
              % (name, "CAUGHT" if ok else "*** SURVIVED ***", n))
        shutil.rmtree(d, ignore_errors=True)
    print("\n%d/%d mutations caught" % (len(MUTS) - survived, len(MUTS)))
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
