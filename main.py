import argparse
import asyncio

from app.multi_agent_runner import run_multi_agent_session
from app.persona import load_persona, load_scenario


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run multi-agent vision-based beta testing with LLaVA."
    )
    parser.add_argument(
        "--persona",
        default="personas/online_shopper.yaml",
        help="Path to persona YAML file (default: online_shopper)",
    )
    parser.add_argument(
        "--scenario",
        default="scenarios/ui_shopping_flow.yaml",
        help="Path to scenario YAML file (default: ui_shopping_flow)",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=4,
        help="Number of agents in the committee (default: 4 - OpenAI, Google, Anthropic, xAI)",
    )

    args = parser.parse_args()

    # Load persona and scenario
    persona = load_persona(args.persona)
    scenario = load_scenario(args.scenario)

    # Run multi-agent session
    result = await run_multi_agent_session(
        persona=persona,
        scenario=scenario,
        num_agents=args.agents,
    )

    # Print final summary
    if result["success"]:
        print("\n🎉 Testing completed successfully!")
    else:
        print("\n⚠️ Testing completed with issues")

    print(f"\n📁 Results saved to: {result['csv_path']}")
    print("🚀 To view results, run: streamlit run dashboard_app.py")


if __name__ == "__main__":
    asyncio.run(main())
