Unit test ownership
- `tests/governance/`: action classification and governance preflight only.
- `tests/trust/`: source classification, trust thresholds, and read-only reader behavior only.
- `tests/memory/`: durable memory and conflict memory ownership only.
- `tests/memory/test_arbitration.py`: canon/provisional/conflict/session arbitration only.
- `tests/memory/test_governed_mutations.py`: rejection, cancellation, prior-state evidence, receipt emission, and continuity ancestry only.
- `tests/memory/test_explanations.py`: preset selection, linked context assembly, bounded linked view generation, attention pressure classification, resolution classification, follow-up classification, grouped attention/resolution/follow-up paging, receipt/timeline selection, pagination/cursor behavior, deterministic ordering, and summary-to-explanation linkage only.
- `tests/context/`: context assembly and filtering only.
- `tests/shell/`: shell bridge and session runtime surfaces only.
- `tests/odin/`: lifecycle orchestration ordering and service coordination only.
- `tests/odin/test_state_signals.py`: burden and stability signal rule logic only.

Integration scope
- `tests/integration/` verifies cross-module product behavior across shell bridge, lifecycle, governance, trust, reader, context, and persistence seams, including durable authority outcomes.
- `tests/integration/test_operator_approved_promotion_flow.py`: operator-approved promotion through shell-shaped product flow only.
- `tests/integration/test_rejected_cancelled_promotion_flow.py`: rejected and cancelled promotion product flow only.
- `tests/integration/test_canon_explanation_flow.py`: shell-safe canon explanation flow only.
- `tests/integration/test_canon_summary_query_flow.py`: shell-safe filtered summary query flow only.
- `tests/integration/test_canon_preset_page_flow.py`: shell-safe preset and paged summary flow only.
- `tests/integration/test_canon_linked_context_flow.py`: shell-safe linked context retrieval and linked-summary drill-down only.
- `tests/integration/test_canon_bounded_view_flow.py`: shell-safe bounded linked preset flow and drill-down only.
- `tests/integration/test_canon_attention_flow.py`: shell-safe attention preset flow, grouped attention retrieval, and drill-down only.
- `tests/integration/test_canon_resolution_flow.py`: shell-safe resolution preset flow, grouped resolution retrieval, and drill-down only.
- `tests/integration/test_canon_followup_flow.py`: shell-safe follow-up preset flow, grouped follow-up retrieval, and drill-down only.

Overlap rule
- Unit tests assert one module's primary behavior.
- Integration tests confirm composed flow and shell-visible outcomes.
- Do not restate unit-level branch assertions inside integration tests unless the cross-module interaction itself is the subject.
