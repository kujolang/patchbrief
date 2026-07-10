# PatchBrief Security Boundary

PatchBrief is a local, read-only Git-reporting tool. It does not make network
or LLM calls, modify the target repository, authenticate to a Git host, or
guarantee detection of secrets, vulnerabilities, or policy violations.

Treat its heuristic risk areas and test suggestions as review leads, not proof.
Run it only in repositories you are authorized to inspect, and review reports
before sharing them because changed paths, commit subjects, and diff-derived
text may be sensitive.
