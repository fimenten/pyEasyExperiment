pyEasyExperiment — simple experiment snapshot + optional MLflow integration

Usage
- Basic snapshotting:
  - Create a folder under `experiments/<uuid>`
  - Save git hash and specified source files (read-only)

Quick start
- Minimal:
  - `from pyeasyexperiment import EasyExperiment`
  - `exp = EasyExperiment()`
  - `exp.start_experiment([__file__])`

MLflow integration (optional)
- Install extras: `pip install .[mlflow]` or `pip install pyeasyexperiment[mlflow]`
- Use MLflow-enabled class:
- `from pyeasyexperiment import MLflowExperiment`
  - `exp = MLflowExperiment(mlflow_experiment="my-exp")`
  - `exp.start_experiment([__file__])`
  - `exp.write_explicit_parms({"lr": 1e-3, "batch": 64})`  # also logs to MLflow
  - `exp.log_metrics({"loss": 0.123}, step=1)`
  - `exp.end_mlflow_run()`

Binary artifacts
- `log_artifact` accepts both file paths and binary data:
  - From path: `exp.log_artifact("/path/to/model.bin", artifact_path="models")`
  - From bytes: `exp.log_artifact(model_bytes, artifact_path="models", filename="model.bin")`
  - From file-like: `exp.log_artifact(buf, artifact_path="models", filename="image.png")`

Notes
- Respects `MLFLOW_TRACKING_URI` and `PYEASYEXPERIMENT_MLFLOW_EXPERIMENT` env vars
- Automatically tags runs with `git.hash` and `pyeasyexperiment.experiment_id`
- For local-snapshot variant (`MLflowExperiment`), also tags `pyeasyexperiment.save_dir` and logs the snapshot folder as MLflow artifacts

With git-commit workflow (cloud-only)
- `from pyeasyexperiment import MLflowExperiment2`
- Commits to the `experiments` branch, starts an MLflow run, and uploads source files directly to MLflow (no local save directory)
