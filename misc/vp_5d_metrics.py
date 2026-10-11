"""Consistent development completion predicate; no scoring or row mutation."""
from misc.vp_cartesian_analyze import completed,metric
from misc.vp_5d_calibration_analysis_02 import wilson

def summarize(rows):
    m=metric(rows)
    return {'requests':m['n'],'completed':m['completed'],'correct':m['correct'],
      'completed_correct':m['completed_correct'],'statuses':m['statuses'],
      'completed_accuracy':m['completed_accuracy'],'all_request_accuracy':m['all_request_accuracy'],
      'completed_wilson_95':wilson(m['completed_correct'],m['completed']) if m['completed'] else None,
      'missing_response_bounds':m['completed_response_bounds_on_all_questions'],
      'truncations':m['truncated'],'families':m['families']}
