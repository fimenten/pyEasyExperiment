from __future__ import annotations

import os
import pathlib
from typing import Dict, Optional, Union, IO
import tempfile

try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    mlflow = None  # type: ignore
    _MLFLOW_AVAILABLE = False

from .easy_experiment import (
    EasyExperiment,
    EasyExperiment2,
    get_git_hash,
    git_commit_all_unstaged,
)
import uuid


class _MLflowMixin:
    """Mixin that adds MLflow helpers to an EasyExperiment subclass.

    This mixin assumes the subclass defines `save_dir` and `experiment_id`.
    """

    def __init__(
        self,
        *args,
        mlflow_enabled: bool = True,
        mlflow_experiment: Optional[str] = None,
        mlflow_tracking_uri: Optional[str] = None,
        mlflow_tags: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self._mlflow_enabled = mlflow_enabled and _MLFLOW_AVAILABLE
        self._mlflow_experiment = (
            mlflow_experiment or os.getenv("PYEASYEXPERIMENT_MLFLOW_EXPERIMENT")
        )
        self._mlflow_tracking_uri = (
            mlflow_tracking_uri or os.getenv("MLFLOW_TRACKING_URI")
        )
        self._mlflow_tags = mlflow_tags or {}
        self._mlflow_run_active = False
        self._mlflow_run_id: Optional[str] = None

    # ---------- public API ----------
    def start_mlflow_run(self) -> Optional[str]:
        if not self._mlflow_enabled:
            return None
        assert _MLFLOW_AVAILABLE and mlflow is not None

        if self._mlflow_tracking_uri:
            mlflow.set_tracking_uri(self._mlflow_tracking_uri)
        if self._mlflow_experiment:
            mlflow.set_experiment(self._mlflow_experiment)

        run = mlflow.start_run(run_name=str(self.experiment_id))
        self._mlflow_run_active = True
        self._mlflow_run_id = run.info.run_id

        # default tags
        default_tags = {
            "pyeasyexperiment.experiment_id": str(self.experiment_id),
            "git.hash": get_git_hash(),
        }
        # Include local save_dir info only when not cloud-only and available
        if not getattr(self, "_cloud_only", False) and hasattr(self, "save_dir"):
            default_tags["pyeasyexperiment.save_dir"] = str(self.save_dir)
        mlflow.set_tags({**default_tags, **self._mlflow_tags})

        # log the whole experiment folder (code snapshot + hash)
        if not getattr(self, "_cloud_only", False) and hasattr(self, "save_dir"):
            if pathlib.Path(self.save_dir).exists():
                mlflow.log_artifacts(str(self.save_dir))

        return self._mlflow_run_id

    def end_mlflow_run(self) -> None:
        if not self._mlflow_enabled:
            return
        if not self._mlflow_run_active:
            return
        assert _MLFLOW_AVAILABLE and mlflow is not None
        mlflow.end_run()
        self._mlflow_run_active = False

    def log_params(self, params: Dict) -> None:
        if not self._MLflowMixin__mlflow_is_on():
            return
        assert _MLFLOW_AVAILABLE and mlflow is not None
        mlflow.log_params(params)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        if not self._MLflowMixin__mlflow_is_on():
            return
        assert _MLFLOW_AVAILABLE and mlflow is not None
        mlflow.log_metrics(metrics, step=step)

    def log_artifact(
        self,
        path_or_data: Union[str, bytes, bytearray, IO[bytes]],
        artifact_path: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> None:
        """Log an artifact to MLflow.

        Accepts either a filesystem path or binary/file-like data.

        - If `path_or_data` is a string path to an existing file, that file is logged.
        - If it's bytes/bytearray or a binary file-like object, you must provide `filename`
          to determine the name within MLflow; the data is written to a temporary file and logged.
        """
        if not self._MLflowMixin__mlflow_is_on():
            return
        assert _MLFLOW_AVAILABLE and mlflow is not None

        # Path-like
        if isinstance(path_or_data, str) and os.path.exists(path_or_data):
            mlflow.log_artifact(path_or_data, artifact_path=artifact_path)
            return

        # Binary-like (bytes/bytearray/file-like)
        if filename is None:
            raise ValueError("filename is required when logging binary or file-like data")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = os.path.join(tmpdir, filename)
            # Ensure parent exists (should, via TemporaryDirectory)
            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)

            if isinstance(path_or_data, (bytes, bytearray)):
                with open(tmp_path, "wb") as f:
                    f.write(path_or_data)
            elif hasattr(path_or_data, "read"):
                with open(tmp_path, "wb") as f:
                    f.write(path_or_data.read())  # type: ignore[arg-type]
            else:
                raise TypeError("path_or_data must be a path, bytes, bytearray, or binary file-like object")

            mlflow.log_artifact(tmp_path, artifact_path=artifact_path)

    # ---------- overrides ----------
    def start_experiment(self, filepath_list=[]):  # type: ignore[override]
        exp_id = super().start_experiment(filepath_list)
        # Start MLflow after experiment dir is ready so we can log it
        self.start_mlflow_run()
        return exp_id

    def write_explicit_parms(self, d: Dict):  # type: ignore[override]
        super().write_explicit_parms(d)
        # Mirror to MLflow params as a convenience
        self.log_params(d)

    # ---------- helpers ----------
    def _MLflowMixin__mlflow_is_on(self) -> bool:
        return self._mlflow_enabled and self._mlflow_run_active and _MLFLOW_AVAILABLE


class MLflowExperiment(_MLflowMixin, EasyExperiment):
    """EasyExperiment with optional MLflow integration.

    Usage:
        exp = MLflowExperiment(mlflow_experiment="my-exp")
        exp.start_experiment([__file__])
        exp.log_metrics({"loss": 0.1}, step=1)
        exp.end_mlflow_run()
    """

    pass


class MLflowExperiment2(_MLflowMixin, EasyExperiment2):
    """EasyExperiment2 (with git commit) + MLflow integration, cloud-only.

    This variant does not create or use any local experiment directory. It only logs
    to MLflow (cloud) and tags runs with the git hash and experiment ID. Source files
    passed to `start_experiment` are uploaded directly to MLflow as artifacts.
    """

    def __init__(
        self,
        *,
        mlflow_enabled: bool = True,
        mlflow_experiment: Optional[str] = None,
        mlflow_tracking_uri: Optional[str] = None,
        mlflow_tags: Optional[Dict[str, str]] = None,
        experiment_id: Optional[str] = None,
    ) -> None:
        # Cloud-only mode: do not initialize EasyExperiment / create local directories
        self._cloud_only = True
        # Minimal identity setup
        self.experiment_id = experiment_id or str(uuid.uuid4())
        # Inline a minimal version of _MLflowMixin.__init__ without chaining to EasyExperiment
        self._mlflow_enabled = mlflow_enabled and _MLFLOW_AVAILABLE
        self._mlflow_experiment = (
            mlflow_experiment or os.getenv("PYEASYEXPERIMENT_MLFLOW_EXPERIMENT")
        )
        self._mlflow_tracking_uri = (
            mlflow_tracking_uri or os.getenv("MLFLOW_TRACKING_URI")
        )
        self._mlflow_tags = mlflow_tags or {}
        self._mlflow_run_active = False
        self._mlflow_run_id = None

    def start_experiment(self, filepath_list=[], commit_message: Optional[str] = None):  # type: ignore[override]
        # Keep the git-commit behavior from EasyExperiment2, but skip local snapshot
        if commit_message is None:
            commit_message = str(self.experiment_id)
        try:
            git_commit_all_unstaged(commit_message)
        except Exception:
            # Non-fatal: proceed even if git commit fails
            pass

        # Start MLflow directly (cloud-only)
        self.start_mlflow_run()

        # Log git hash as a small artifact for traceability
        try:
            gh = get_git_hash()
            self.log_artifact(gh.encode("utf-8"), filename="git_hash.txt")
        except Exception:
            pass

        # Upload provided source files to MLflow under "source" path
        for p in filepath_list or []:
            try:
                if isinstance(p, str) and os.path.exists(p):
                    self.log_artifact(p, artifact_path="source")
            except Exception:
                # Continue logging other files even if one fails
                continue

        return str(self.experiment_id)

    def write_explicit_parms(self, d: Dict):  # type: ignore[override]
        # Cloud-only: do not write to local files; mirror to MLflow only
        self.log_params(d)
