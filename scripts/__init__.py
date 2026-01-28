_version__ = "1.0.0"
__author__ = "Data Analyst"

from .analysis import (
    load_data,
    calculate_metrics,
    get_metrics_by_category,
    print_metrics_report,
    print_category_report,
    ensure_output_dir,
    get_timestamp,
    log_message,
)

from .visualizations import (
    save_figure,
    close_and_save,
    plot_sla_chart,
    plot_category_distribution,
    plot_resolution_distribution,
    save_all_visualizations,
)

__all__ = [
    # analysis functions
    'load_data',
    'calculate_metrics',
    'get_metrics_by_category',
    'print_metrics_report',
    'print_category_report',
    'ensure_output_dir',
    'get_timestamp',
    'log_message',
    # visualization functions
    'save_figure',
    'close_and_save',
    'plot_sla_chart',
    'plot_category_distribution',
    'plot_resolution_distribution',
    'save_all_visualizations',
]
