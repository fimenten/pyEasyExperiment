from __future__ import annotations

import os
import pathlib
from typing import Dict, Optional, Union, IO, List
import tempfile
import sys
import shlex

try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except Exception:
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
        default_tags = {
            "pyeasyexperiment.experiment_id": str(self.experiment_id),
            "git.hash": get_git_hash(),
        }
        if not getattr(self, "_cloud_only", False) and hasattr(self, "save_dir"):
            default_tags["pyeasyexperiment.save_dir"] = str(self.save_dir)
        mlflow.set_tags({**default_tags, **self._mlflow_tags})
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
        if not self._MLflowMixin__mlflow_is_on():
            return
        assert _MLFLOW_AVAILABLE and mlflow is not None
        if isinstance(path_or_data, str) and os.path.exists(path_or_data):
            mlflow.log_artifact(path_or_data, artifact_path=artifact_path)
            return
        if filename is None:
            filename = str(uuid.uuid4())
            raise Warning(f"filename is required when logging binary or file-like data, named {filename}")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = os.path.join(tmpdir, filename)
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

    def start_experiment(self, filepath_list=[]):  # type: ignore[override]
        exp_id = super().start_experiment(filepath_list)
        self.start_mlflow_run()
        self.record_run_command()
        return exp_id

    def write_explicit_parms(self, d: Dict):  # type: ignore[override]
        super().write_explicit_parms(d)
        self.log_params(d)

    def record_run_command(self, command: Optional[str] = None, env_keys: Optional[List[str]] = None) -> Optional[str]:
        cmd = self._build_invocation_command(command)
        if not cmd:
            return None
        try:
            if not getattr(self, "_cloud_only", False) and hasattr(self, "save_dir"):
                p = pathlib.Path(self.save_dir) / "run_command.txt"
                p.write_text(cmd, encoding="utf-8")
        except Exception:
            pass
        try:
            self.log_params({"run.command": cmd})
        except Exception:
            pass
        try:
            self.log_artifact(cmd.encode("utf-8"), filename="run_command.txt")
        except Exception:
            pass
        if env_keys:
            try:
                lines = []
                for k in env_keys:
                    v = os.getenv(k, "")
                    lines.append(f"{k}={v}")
                env_txt = "\n".join(lines).encode("utf-8")
                self.log_artifact(env_txt, filename="run_env_subset.txt")
            except Exception:
                pass
        return cmd

    def _build_invocation_command(self, explicit_command: Optional[str]) -> str:
        if explicit_command:
            return explicit_command
        try:
            exe = os.environ.get("PYEASYEXPERIMENT_CMD_EXE") or sys.executable or "python"
            pre = os.environ.get("PYEASYEXPERIMENT_CMD_PREFIX", "")
            argv_env = os.environ.get("PYEASYEXPERIMENT_CMD")
            if argv_env:
                return argv_env
            parts = [shlex.quote(exe)] + [shlex.quote(a) for a in sys.argv]
            if pre:
                return f"{pre} {' '.join(parts)}"
            return " ".join(parts)
        except Exception:
            return ""

    def _MLflowMixin__mlflow_is_on(self) -> bool:
        return self._mlflow_enabled and self._mlflow_run_active and _MLFLOW_AVAILABLE


class MLflowExperiment(_MLflowMixin, EasyExperiment):
    pass


class MLflowExperiment2(_MLflowMixin, EasyExperiment2):
    def __init__(
        self,
        *,
        mlflow_enabled: bool = True,
        mlflow_experiment: Optional[str] = None,
        mlflow_tracking_uri: Optional[str] = None,
        mlflow_tags: Optional[Dict[str, str]] = None,
        experiment_id: Optional[str] = None,
    ) -> None:
        self._cloud_only = True
        self.experiment_id = experiment_id or str(uuid.uuid4())
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
        if commit_message is None:
            commit_message = str(self.experiment_id)
        try:
            git_commit_all_unstaged(commit_message)
        except Exception:
            pass
        self.start_mlflow_run()
        try:
            gh = get_git_hash()
            self.log_artifact(gh.encode("utf-8"), filename="git_hash.txt")
        except Exception:
            pass
        for p in filepath_list or []:
            try:
                if isinstance(p, str) and os.path.exists(p):
                    self.log_artifact(p, artifact_path="source")
            except Exception:
                continue
        self.record_run_command()
        return str(self.experiment_id)

    def write_explicit_parms(self, d: Dict):  # type: ignore[override]
        self.log_params(d)
