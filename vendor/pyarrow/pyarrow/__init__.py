"""Satisfy Streamlit's pyarrow dependency without shipping the real 160MB+ wheel.

Raising ImportError keeps pandas/Streamlit on their non-Arrow code paths.
TutorRAG does not use dataframe / Arrow APIs.
"""

raise ImportError(
    "TutorRAG ships a deploy-size stub instead of the full pyarrow wheel. "
    "Arrow dataframe features are unavailable in this build."
)
