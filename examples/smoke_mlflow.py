import os
import io
import pathlib

from pyeasyexperiment import MLflowExperiment


def main():
    # Show current MLflow config from env
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    exp_name = os.getenv("PYEASYEXPERIMENT_MLFLOW_EXPERIMENT", "demo-experiment")
    print(f"MLFLOW_TRACKING_URI={tracking_uri}")
    print(f"PYEASYEXPERIMENT_MLFLOW_EXPERIMENT={exp_name}")

    exp = MLflowExperiment(mlflow_experiment=exp_name)
    exp_id = exp.start_experiment([__file__])
    print(f"Started experiment: {exp_id} at {exp.save_dir}")

    # Params and metrics
    exp.write_explicit_parms({"lr": 1e-3, "batch": 8})
    exp.log_metrics({"loss": 0.321, "acc": 0.88}, step=1)

    # Binary artifact from bytes
    data = b"hello-mlflow-from-bytes"
    exp.log_artifact(data, artifact_path="artifacts", filename="hello.bin")

    # Binary artifact from file-like
    buf = io.BytesIO(b"in-memory-file-like-content")
    exp.log_artifact(buf, artifact_path="artifacts", filename="buffer.txt")

    # Path artifact (create a small file)
    path = pathlib.Path(exp.save_dir) / "note.txt"
    path.write_text("This is a note saved alongside the snapshot.")
    exp.log_artifact(str(path), artifact_path="artifacts")

    exp.end_mlflow_run()
    print("MLflow run ended.")


if __name__ == "__main__":
    main()

