# Phase 3 Context

Goal: Improve relationship inference quality beyond exact-tag matching so research output is more useful and explainable.

Current limitations:
- same_theme links require identical tag sets
- no structured evidence payload exists
- confidence/risk logic is static and shallow

Target:
- preserve mutually_exclusive rule
- make same_theme inference more flexible using category plus overlapping tags
- attach structured evidence details to each relationship
- keep the implementation small and deterministic
