"""
Demo runner for LLM beta testing framework.

Supports both single-agent and multi-agent modes with optional reporting.
"""

import argparse

from agent import LLMUserAgent
from aut_adapter import APIAdapter
from config import settings
from llm import LLM
from orchestrator import run_session
from persona_loader import compose_persona, load_yaml
import reporter


def main():
    parser = argparse.ArgumentParser(description="Run LLM beta testing demo")
    parser.add_argument(
        "--persona",
        default="config/default.yaml",
        help="Path to persona YAML file",
    )
    parser.add_argument(
        "--scenario",
        default="config/scenario_demo.yaml",
        help="Path to scenario YAML file",
    )
    parser.add_argument(
        "--multi-agent",
        action="store_true",
        help="Use multi-agent committee mode",
    )
    parser.add_argument(
        "--version",
        default="v1.0",
        help="Version tag for tracking",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate report after run",
    )
    parser.add_argument(
        "--baseline",
        help="Baseline session ID for regression comparison",
    )
    parser.add_argument(
        "--candidate",
        help="Candidate session ID for regression comparison",
    )
    
    args = parser.parse_args()
    
    # Regression comparison mode
    if args.baseline and args.candidate:
        print(f"\n🔍 Generating regression diff: {args.baseline} vs {args.candidate}\n")
        diff_report = reporter.build_regression_diff(args.baseline, args.candidate)
        reporter.save_reports(diff_report, settings.reports_dir)
        print(f"✅ Regression diff saved to {settings.reports_dir}/")
        print(f"   Verdict: {diff_report['verdict']}")
        return
    
    # Load persona and scenario
    persona = compose_persona(args.persona)
    scenario_data = load_yaml(args.scenario)
    initial_obs = scenario_data.get("initial_observation", "System ready.")
    
    print(f"\n🧪 Starting beta test session")
    print(f"   Persona: {persona.name}")
    print(f"   Goals: {', '.join(persona.goals)}")
    print(f"   Version: {args.version}")
    print(f"   Multi-agent: {args.multi_agent}")
    print()
    
    # Setup
    if args.multi_agent:
        # Multi-agent mode
        result = run_session(
            persona=persona,
            initial_observation=initial_obs,
            adapter=APIAdapter(),
            max_turns=settings.max_turns,
            use_multi_agent=True,
            version=args.version,
            scenario=scenario_data.get("name", "demo"),
        )
    else:
        # Single agent mode
        llm = LLM()
        agent = LLMUserAgent(llm, persona)
        
        result = run_session(
            persona=persona,
            initial_observation=initial_obs,
            agent=agent,
            adapter=APIAdapter(),
            max_turns=settings.max_turns,
            use_multi_agent=False,
            version=args.version,
            scenario=scenario_data.get("name", "demo"),
        )
    
    print(f"\n✅ Session complete!")
    print(f"   Session ID: {result['session_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Turns: {result['turns_executed']}/{settings.max_turns}")
    print(f"   Success: {result['success']}")
    
    # Generate report if requested
    if args.report:
        print(f"\n📊 Generating report...")
        run_report = reporter.build_run_report(result['session_id'])
        reporter.save_reports(run_report, settings.reports_dir)
        
        print(f"   Task Success Rate: {run_report['metrics']['task_success_rate']:.1%}")
        print(f"   Latency p50: {run_report['metrics']['latency']['p50']:.3f}s")
        print(f"   Reports saved to: {settings.reports_dir}/")
        print(f"     - {result['session_id']}.json")
        print(f"     - {result['session_id']}.md")
    
    print(f"\n💡 Tip: Use --report to generate detailed metrics")
    print(f"   or compare with: --baseline {result['session_id']} --candidate <other_id>\n")


if __name__ == "__main__":
    main()
