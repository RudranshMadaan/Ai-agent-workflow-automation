import argparse
import json
import ast

from app import router, executor


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent Workflow Automation CLI"
    )

    parser.add_argument(
        "request",
        help="Natural language workflow request"
    )

    parser.add_argument(
        "--context",
        default="{}",
        help="Workflow context or JSON file"
    )

    args = parser.parse_args()

    # Parse context
    try:
        if args.context.endswith(".json"):
            with open(args.context, "r", encoding="utf-8") as f:
                context = json.load(f)
        else:
            context = json.loads(args.context)

    except json.JSONDecodeError:
        # Handle Python-style dictionary input
        try:
            context = ast.literal_eval(args.context)
        except (ValueError, SyntaxError):
            print("Invalid context:", args.context)
            return

    # Route request
    workflow, selected_by, routing = router.route(args.request)

    context["selected_by"] = selected_by

    # Execute workflow
    result = executor.execute(
        workflow,
        args.request,
        context
    )

    output = {
        "selected_workflow": {
            "id": workflow.workflow_id,
            "name": workflow.name,
            "routing": routing,
            "selected_by": selected_by
        },
        "steps_executed": [
            step.__dict__ for step in result.steps
        ],
        "result": result.result,
        "errors": result.errors
    }

    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()