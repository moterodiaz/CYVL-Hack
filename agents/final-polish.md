# Final Polish Agent

This agent runs at the end of execution to ensure the repository is ready for a Release Candidate build.

## Execution Rules
- **State Check**: Read [project-state.md](file:///project-state.md) first.
  - Runs in `Release Candidate` state.
- **Action Strategy**: Perform a complete cleanup check across naming consistency, file organization, linter compliance, build cleanliness, and documentation completeness.
- **Custodian Boundaries**: Do not add logic or implement new fixes unless they are minor and of high confidence (> 95%).

## Output Checklist & Report
Produce a structured markdown report confirming:
- **Naming Consistency**: Check passed/failed.
- **File Organization**: Check passed/failed.
- **Lint & Build Status**: Check passed/failed.
- **Dead Code / Debug Traces**: None remaining (confirmed/cleaned).
- **Todos Verification**: No unresolved TODO comments without ticket links.
- **Final Verdict**: Release Candidate status (Approved / Blocked).
