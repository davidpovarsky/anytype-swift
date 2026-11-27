"""Original same-job binding; one explicit independent output namespace."""
import os
from pathlib import Path
import re
from admission import REPOSITORY, canonical
from profile import require


def bind_job(args, plan):
    env = os.environ
    require(env.get("GITHUB_REPOSITORY") == REPOSITORY and env.get("GITHUB_ACTIONS") == "true"
            and env.get("RUNNER_ENVIRONMENT") == "github-hosted" and env.get("RUNNER_ARCH") == "ARM64",
            "The original GitHub-hosted ARM64 job is required")
    run, attempt = env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_RUN_ATTEMPT", "")
    require(re.fullmatch(r"[1-9][0-9]*", run) and re.fullmatch(r"[1-9][0-9]*", attempt)
            and env.get("GITHUB_JOB"), "Actual original run/attempt/job identity is required")
    workspace = canonical(env["GITHUB_WORKSPACE"], directory=True)
    temporary = canonical(env["RUNNER_TEMP"], directory=True)
    require(Path(args.control) == workspace / "control" and Path(args.source) == workspace / "app/source"
            and Path(args.build_root) == temporary / ("pinkha-hosted-shared-" + run + "-" + attempt)
            and Path(args.plan) == temporary / "pinkha-root-plan.json"
            and Path(args.output) == temporary / ("pinkha-hosted-t5-" + run + "-" + attempt),
            "Different-job, relocated or invented producer paths are not supported")
    require(plan["controlCommit"] == env.get("GITHUB_SHA") and plan["repository"] == REPOSITORY
            and plan["readyForBuild"] is True and plan["schema"] == "pinkha-hosted-original-shared-build-plan-v1",
            "Exact root-reviewed executed hosted plan required")
    require(env.get("DEVELOPER_DIR") == plan["toolchain"]["developerDir"],
            "Runtime must use the producer's exact selected Xcode")
    return {"repository": REPOSITORY, "runID": run, "runAttempt": attempt,
            "job": env["GITHUB_JOB"], "controlCommit": env["GITHUB_SHA"],
            "workspace": str(workspace), "temporary": str(temporary),
            "developerDir": env["DEVELOPER_DIR"]}
