"""
pyEasyExperiment - A simple experiment tracking library
"""

from .easy_experiment import EasyExperiment, EasyExperiment2
from .mlflow_integration import MLflowExperiment, MLflowExperiment2

__version__ = "0.1.0"
__all__ = [
    "EasyExperiment",
    "EasyExperiment2",
    "MLflowExperiment",
    "MLflowExperiment2",
]
