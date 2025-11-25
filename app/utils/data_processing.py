"""
Data Processing Utilities Module

This module demonstrates integration with popular Python libraries:
- NumPy for numerical computing
- Pandas for data manipulation
- Data validation and transformation

Usage:
    from app.utils.data_processing import (
        analyze_numerical_data,
        process_dataframe,
        generate_statistics
    )
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from app.core.logging import get_logger

logger = get_logger(__name__)


def analyze_numerical_data(data: List[float]) -> Dict[str, float]:
    """
    Analyze numerical data using NumPy.
    
    Demonstrates NumPy integration for statistical analysis.
    
    Args:
        data: List of numerical values
        
    Returns:
        Dictionary with statistical measures
        
    Example:
        >>> data = [1.0, 2.0, 3.0, 4.0, 5.0]
        >>> stats = analyze_numerical_data(data)
        >>> print(stats["mean"], stats["std"])
    """
    if not data:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "count": 0
        }
    
    arr = np.array(data)
    
    result = {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "count": len(arr),
        "sum": float(np.sum(arr)),
        "percentile_25": float(np.percentile(arr, 25)),
        "percentile_75": float(np.percentile(arr, 75)),
    }
    
    logger.debug("Numerical analysis completed", data_points=len(data))
    return result


def process_dataframe(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process data using Pandas DataFrame.
    
    Demonstrates Pandas integration for data manipulation.
    
    Args:
        data: List of dictionaries representing rows
        
    Returns:
        Dictionary with processed data and statistics
        
    Example:
        >>> data = [
        ...     {"name": "Alice", "age": 30, "score": 85},
        ...     {"name": "Bob", "age": 25, "score": 92}
        ... ]
        >>> result = process_dataframe(data)
    """
    if not data:
        return {"error": "No data provided"}
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    result: Dict[str, Any] = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
    }
    
    # Get numerical columns statistics
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        result["numeric_summary"] = df[numeric_cols].describe().to_dict()
    
    # Get categorical columns info
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    if categorical_cols:
        result["categorical_info"] = {
            col: {
                "unique_count": df[col].nunique(),
                "most_common": df[col].mode()[0] if not df[col].mode().empty else None
            }
            for col in categorical_cols
        }
    
    logger.debug(
        "DataFrame processing completed",
        rows=len(df),
        columns=len(df.columns)
    )
    
    return result


def calculate_correlation_matrix(data: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Calculate correlation matrix for numerical data.
    
    Demonstrates correlation analysis with Pandas.
    
    Args:
        data: List of dictionaries with numerical values
        
    Returns:
        Correlation matrix as dictionary
        
    Example:
        >>> data = [
        ...     {"x": 1, "y": 2, "z": 3},
        ...     {"x": 2, "y": 4, "z": 6},
        ...     {"x": 3, "y": 6, "z": 9}
        ... ]
        >>> corr = calculate_correlation_matrix(data)
    """
    if not data:
        return {"error": "No data provided"}
    
    df = pd.DataFrame(data)
    numeric_df = df.select_dtypes(include=[np.number])
    
    if numeric_df.empty:
        return {"error": "No numerical columns found"}
    
    correlation_matrix = numeric_df.corr()
    
    result = {
        "correlation_matrix": correlation_matrix.to_dict(),
        "highly_correlated_pairs": []
    }
    
    # Find highly correlated pairs (|correlation| > 0.7)
    for i in range(len(correlation_matrix.columns)):
        for j in range(i + 1, len(correlation_matrix.columns)):
            col1 = correlation_matrix.columns[i]
            col2 = correlation_matrix.columns[j]
            corr_value = correlation_matrix.iloc[i, j]
            
            if abs(corr_value) > 0.7:
                result["highly_correlated_pairs"].append({
                    "column1": col1,
                    "column2": col2,
                    "correlation": float(corr_value)
                })
    
    logger.debug("Correlation analysis completed", columns=len(numeric_df.columns))
    return result


def aggregate_data(
    data: List[Dict[str, Any]],
    group_by: str,
    agg_column: str,
    agg_func: str = "mean"
) -> List[Dict[str, Any]]:
    """
    Aggregate data by a grouping column.
    
    Demonstrates group-by operations with Pandas.
    
    Args:
        data: List of dictionaries
        group_by: Column to group by
        agg_column: Column to aggregate
        agg_func: Aggregation function (mean, sum, count, min, max)
        
    Returns:
        List of aggregated results
        
    Example:
        >>> data = [
        ...     {"category": "A", "value": 10},
        ...     {"category": "A", "value": 20},
        ...     {"category": "B", "value": 15}
        ... ]
        >>> result = aggregate_data(data, "category", "value", "sum")
    """
    if not data:
        return []
    
    df = pd.DataFrame(data)
    
    if group_by not in df.columns or agg_column not in df.columns:
        logger.warning(
            "Invalid columns for aggregation",
            group_by=group_by,
            agg_column=agg_column
        )
        return []
    
    # Map aggregation function
    agg_functions = {
        "mean": "mean",
        "sum": "sum",
        "count": "count",
        "min": "min",
        "max": "max",
        "std": "std"
    }
    
    func = agg_functions.get(agg_func, "mean")
    
    # Perform aggregation
    result_df = df.groupby(group_by)[agg_column].agg(func).reset_index()
    result_df.columns = [group_by, f"{agg_func}_{agg_column}"]
    
    result = result_df.to_dict('records')
    
    logger.debug(
        "Data aggregation completed",
        group_by=group_by,
        agg_column=agg_column,
        agg_func=agg_func,
        groups=len(result)
    )
    
    return result


def filter_outliers(
    data: List[float],
    method: str = "iqr",
    threshold: float = 1.5
) -> Dict[str, Any]:
    """
    Filter outliers from numerical data.
    
    Demonstrates outlier detection using statistical methods.
    
    Args:
        data: List of numerical values
        method: Detection method ("iqr" or "zscore")
        threshold: Threshold for outlier detection
        
    Returns:
        Dictionary with filtered data and outliers
        
    Example:
        >>> data = [1, 2, 3, 4, 5, 100]  # 100 is an outlier
        >>> result = filter_outliers(data, method="iqr")
        >>> print(result["outliers"])
    """
    if not data:
        return {"filtered_data": [], "outliers": [], "outlier_count": 0}
    
    arr = np.array(data)
    
    if method == "iqr":
        # Interquartile Range method
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        mask = (arr >= lower_bound) & (arr <= upper_bound)
    
    elif method == "zscore":
        # Z-score method
        mean = np.mean(arr)
        std = np.std(arr)
        
        if std == 0:
            mask = np.ones(len(arr), dtype=bool)
        else:
            z_scores = np.abs((arr - mean) / std)
            mask = z_scores <= threshold
    
    else:
        logger.warning("Unknown outlier detection method", method=method)
        mask = np.ones(len(arr), dtype=bool)
    
    filtered_data = arr[mask].tolist()
    outliers = arr[~mask].tolist()
    
    result = {
        "filtered_data": filtered_data,
        "outliers": outliers,
        "outlier_count": len(outliers),
        "original_count": len(data),
        "method": method,
        "threshold": threshold
    }
    
    logger.debug(
        "Outlier filtering completed",
        original_count=len(data),
        outliers_removed=len(outliers),
        method=method
    )
    
    return result


def normalize_data(
    data: List[float],
    method: str = "minmax"
) -> Dict[str, Any]:
    """
    Normalize numerical data.
    
    Args:
        data: List of numerical values
        method: Normalization method ("minmax" or "zscore")
        
    Returns:
        Dictionary with normalized data
        
    Example:
        >>> data = [1, 2, 3, 4, 5]
        >>> result = normalize_data(data, method="minmax")
        >>> # Result will be values between 0 and 1
    """
    if not data:
        return {"normalized_data": [], "method": method}
    
    arr = np.array(data)
    
    if method == "minmax":
        # Min-Max normalization to [0, 1]
        min_val = np.min(arr)
        max_val = np.max(arr)
        
        if max_val - min_val == 0:
            normalized = np.zeros_like(arr)
        else:
            normalized = (arr - min_val) / (max_val - min_val)
    
    elif method == "zscore":
        # Z-score normalization (standardization)
        mean = np.mean(arr)
        std = np.std(arr)
        
        if std == 0:
            normalized = np.zeros_like(arr)
        else:
            normalized = (arr - mean) / std
    
    else:
        logger.warning("Unknown normalization method", method=method)
        normalized = arr
    
    result = {
        "normalized_data": normalized.tolist(),
        "method": method,
        "original_min": float(np.min(arr)),
        "original_max": float(np.max(arr)),
        "original_mean": float(np.mean(arr)),
        "original_std": float(np.std(arr))
    }
    
    logger.debug("Data normalization completed", method=method, count=len(data))
    return result
