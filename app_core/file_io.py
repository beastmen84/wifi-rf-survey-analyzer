"""Atomic single-file writes and recoverable, journaled survey saves."""

import json
import hashlib
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


def file_digest(path):
    if not path.exists():
        return None
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def survey_file_lock(csv_file):
    """Serialize recovery/save operations; retain the lock inode between uses."""
    path = Path(csv_file).absolute()
    lock_path = path.with_name(f".{path.name}.save.lock")
    with open(lock_path, "a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class SurveyFileTransaction:
    """Stage files beside a CSV and roll back an interrupted commit on reopen.

    The journal is installed only after all stages and backups are complete.
    Until the committed marker is durable, recovery restores the previous set.
    This is recovery for multiple files, not a filesystem-wide atomic rename.
    """

    def __init__(self, csv_file):
        self.csv_file = Path(csv_file).absolute()
        self.journal = self.csv_file.with_name(f".{self.csv_file.name}.save.json")
        self.lock_path = self.csv_file.with_name(f".{self.csv_file.name}.save.lock")
        self.token = uuid4().hex
        self.entries = []

    def __enter__(self):
        self.lock = survey_file_lock(self.csv_file)
        self.lock.__enter__()
        try:
            self.recover()
        except BaseException:
            self.lock.__exit__(*sys.exc_info())
            raise
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            # Preserve the journal/backups if rollback failed, for later recovery.
            if not self.journal.exists():
                self._cleanup(self.entries)
        finally:
            self.lock.__exit__(exc_type, exc, traceback)

    def stage_file(self, destination):
        destination = Path(destination).absolute()
        if destination.parent != self.csv_file.parent:
            raise ValueError("Survey sidecars must be beside the CSV")
        if destination in (self.journal, self.lock_path):
            raise ValueError("Reserved survey save destination")
        if any(self._path(entry["target"]) == destination for entry in self.entries):
            raise ValueError(f"Duplicate survey destination: {destination.name}")
        prefix = f".{destination.name}.{self.token}"
        entry = dict(target=destination.name, stage=prefix + ".stage" + destination.suffix,
                     backup=prefix + ".backup", existed=destination.exists())
        self.entries.append(entry)
        return destination.with_name(entry["stage"])

    def _path(self, name):
        return self.csv_file.with_name(name)

    def commit(self):
        for entry in self.entries:
            with open(self._path(entry["stage"]), "r+b") as stream:
                os.fsync(stream.fileno())
            if entry["existed"]:
                shutil.copy2(self._path(entry["target"]), self._path(entry["backup"]))
                with open(self._path(entry["backup"]), "r+b") as stream:
                    os.fsync(stream.fileno())
            entry["old_sha256"] = file_digest(self._path(entry["backup"])) if entry["existed"] else None
            entry["new_sha256"] = file_digest(self._path(entry["stage"]))
        payload = dict(version=1, token=self.token, state="prepared", files=self.entries)
        self._validated_entries(payload)
        atomic_write_text(self.journal, json.dumps(payload))
        try:
            for entry in self.entries:
                os.replace(self._path(entry["stage"]), self._path(entry["target"]))
            payload["state"] = "committed"
            atomic_write_text(self.journal, json.dumps(payload))
        except BaseException:
            self.recover()
            raise
        # Cleanup failures must not turn a completed save into an apparent failure.
        self._cleanup(self.entries, journal=self.journal)

    def recover(self):
        if not self.journal.exists():
            return
        payload = json.loads(self.journal.read_text(encoding="utf-8"))
        entries = self._validated_entries(payload)
        if payload["state"] == "prepared":
            # Validate the whole recovery set before touching any destination.
            # A changed target or damaged backup requires manual attention,
            # never deletion/overwrite of an unrelated newer file.
            for entry in entries:
                current = file_digest(self._path(entry["target"]))
                if current not in {None, entry["old_sha256"], entry["new_sha256"]}:
                    raise OSError(f"Survey file changed since interrupted save: {entry['target']}")
                if entry["existed"] and file_digest(self._path(entry["backup"])) != entry["old_sha256"]:
                    raise OSError(f"Survey backup is missing or damaged: {entry['target']}")
            for entry in entries:
                target = self._path(entry["target"])
                if entry["existed"]:
                    # Keep the backup until the whole rollback succeeds, so retry
                    # remains safe even if another error interrupts recovery.
                    restore = self._path(entry["backup"] + ".restore")
                    shutil.copy2(self._path(entry["backup"]), restore)
                    os.replace(restore, target)
                else:
                    target.unlink(missing_ok=True)
        self._cleanup(entries, journal=self.journal, strict=True)

    def _validated_entries(self, payload):
        token = payload.get("token", "")
        if (payload.get("version") != 1 or payload.get("state") not in {"prepared", "committed"}
                or len(token) != 32 or any(c not in "0123456789abcdef" for c in token)):
            raise ValueError("Invalid survey save journal")
        entries = payload.get("files")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Invalid survey save journal")
        targets = set()
        for entry in entries:
            target = entry.get("target", "")
            if (not target or target in {".", ".."} or Path(target).name != target
                    or any(c in target for c in '/\\:') or os.path.normcase(target) in targets
                    or self._path(target) in (self.journal, self.lock_path)
                    or not isinstance(entry.get("existed"), bool)):
                raise ValueError("Invalid survey save destination")
            targets.add(os.path.normcase(target))
            prefix = f".{target}.{token}"
            if (entry.get("stage") != prefix + ".stage" + Path(target).suffix
                    or entry.get("backup") != prefix + ".backup"):
                raise ValueError("Invalid survey save backup")
            for key in ("old_sha256", "new_sha256"):
                digest = entry.get(key)
                if key == "old_sha256" and not entry["existed"] and digest is None:
                    continue
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                    raise ValueError("Invalid survey save checksum")
        if os.path.normcase(self.csv_file.name) not in targets:
            raise ValueError("Survey save journal does not contain its CSV")
        return entries

    def _cleanup(self, entries, journal=None, strict=False):
        # Remove the journal first only after recovery/commit has succeeded.
        # Any remaining backup is then harmless, never a recovery instruction.
        try:
            if journal:
                journal.unlink(missing_ok=True)
            for entry in entries:
                for key in ("stage", "backup"):
                    self._path(entry[key]).unlink(missing_ok=True)
                self._path(entry["backup"] + ".restore").unlink(missing_ok=True)
        except OSError:
            if strict:
                raise


def recover_survey_save(csv_file):
    path = Path(csv_file)
    if path.with_name(f".{path.name}.save.json").exists():
        with SurveyFileTransaction(csv_file):
            pass
