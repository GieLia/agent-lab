import json
import os

from pathlib import Path
from urllib.parse import urlparse


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

CASE_PATH = (
    ROOT
    / "tests"
    / "evals"
    / "real_graph"
    / "cases"
    / "e5_f2_ot_01.json"
)


def load_json(
    path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main():

    run_id = os.environ.get(
        "RUN_ID"
    )

    if not run_id:
        raise SystemExit(
            "RUN_ID is required"
        )

    case = load_json(
        CASE_PATH
    )

    requirements = (
        case[
            "benchmark_requirements"
        ]
    )

    run_dir = (
        ROOT
        / "runs"
        / "research-graph-v1"
        / run_id
    )

    required_files = [
        "summary.json",
        "worker_result.json",
        "verification_summary.json",
        "acceptance_gate.json",
        "synthesis_result.json",
        "final.md",
    ]

    missing = [
        name
        for name in required_files
        if not (
            run_dir
            / name
        ).exists()
    ]

    assert not missing, (
        "missing artifacts: "
        + str(
            missing
        )
    )

    summary = load_json(
        run_dir
        / "summary.json"
    )

    worker = load_json(
        run_dir
        / "worker_result.json"
    )

    verification = load_json(
        run_dir
        / "verification_summary.json"
    )

    gate = load_json(
        run_dir
        / "acceptance_gate.json"
    )


    # ----- source quality envelope -----

    sources = worker[
        "sources"
    ]

    assert (
        len(
            sources
        )
        >= requirements[
            "min_sources"
        ]
    ), (
        "insufficient source count: "
        + str(
            len(
                sources
            )
        )
    )


    domains = set()

    for source in sources:

        url = source.get(
            "url"
        )

        assert isinstance(
            url,
            str,
        )

        hostname = (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

        assert hostname

        domains.add(
            hostname
        )

        metadata = source.get(
            "metadata",
            {}
        )

        assert (
            metadata.get(
                "search_discovered"
            )
            is True
        )

        assert (
            metadata.get(
                "status_code"
            )
            == 200
        )


    assert (
        len(
            domains
        )
        >= requirements[
            "min_independent_domains"
        ]
    ), (
        "insufficient domain diversity: "
        + str(
            sorted(
                domains
            )
        )
    )


    # ----- claim envelope -----

    claims = worker[
        "claims"
    ]

    assert (
        requirements[
            "min_claims"
        ]
        <= len(
            claims
        )
        <= requirements[
            "max_claims"
        ]
    ), (
        "claim count outside benchmark "
        "range: "
        + str(
            len(
                claims
            )
        )
    )


    if requirements[
        "require_all_claims_fact"
    ]:

        assert all(
            claim.get(
                "claim_type"
            )
            == "fact"
            for claim in claims
        )


    # ----- semantic/runtime verification -----

    results = verification[
        "claim_results"
    ]

    assert len(
        results
    ) == len(
        claims
    )

    if requirements[
        "require_all_factual_claims_runtime_verified"
    ]:

        assert all(
            result.get(
                "runtime_verification_status"
            )
            == "verified"
            for result in results
        )


    atomicity = []

    for result in results:

        verdicts = result.get(
            "semantic_verdicts",
            []
        )

        assert verdicts

        for verdict in verdicts:

            value = (
                verdict[
                    "evaluation"
                ][
                    "claim_atomicity"
                ]
            )

            atomicity.append(
                value
            )


    if requirements[
        "require_all_factual_claims_atomic"
    ]:

        assert all(
            value == "atomic"
            for value in atomicity
        ), (
            "compound factual claim "
            "detected: "
            + str(
                atomicity
            )
        )


    # ----- acceptance / synthesis -----

    assert (
        gate[
            "decision"
        ]
        == requirements[
            "require_acceptance"
        ]
    )

    assert (
        set(
            gate[
                "accepted_claim_ids"
            ]
        )
        == {
            claim[
                "claim_id"
            ]
            for claim in claims
        }
    )


    # ----- runtime measurement -----

    measurement = summary[
        "measurement"
    ]

    assert (
        measurement[
            "transport_failure_invocation_count"
        ]
        == requirements[
            "require_transport_failures"
        ]
    )

    usage = measurement.get(
        "usage"
    )

    assert isinstance(
        usage,
        dict,
    )

    if requirements[
        "require_cost_complete"
    ]:

        assert (
            usage[
                "cost_complete"
            ]
            is True
        )

    assert float(
        usage[
            "reported_cost_usd"
        ]
    ) > 0


    metrics = summary[
        "research_metrics"
    ]

    assert (
        metrics[
            "search_calls"
        ]
        >= requirements[
            "require_research_search_calls_min"
        ]
    )

    assert (
        metrics[
            "fetch_calls"
        ]
        >= requirements[
            "require_research_fetch_calls_min"
        ]
    )


    print(
        "OT_BENCHMARK_SOURCE_COUNT_OK"
    )

    print(
        "OT_BENCHMARK_DOMAIN_DIVERSITY_OK"
    )

    print(
        "OT_BENCHMARK_ATOMIC_CLAIMS_OK"
    )

    print(
        "OT_BENCHMARK_FULL_VERIFICATION_OK"
    )

    print(
        "OT_BENCHMARK_ACCEPTANCE_OK"
    )

    print(
        "OT_BENCHMARK_COST_COMPLETE_OK"
    )

    print(
        "OT_BENCHMARK_FINAL_ARTIFACT_OK"
    )

    print()
    print(
        "E5_F2_OT_01_PASS"
    )


if __name__ == "__main__":
    main()
