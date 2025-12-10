"""Multi-agent committee-based test session runner."""
from __future__ import annotations

from typing import Dict, List

from rich import print as rprint

from config import settings
from .browser_adapter import BrowserAdapter
from .multi_agent_committee import MultiAgentCommittee
from .schemas import Persona, Action
from .storage import SessionStorage
from .validators import validate_action


async def run_multi_agent_session(
    persona: Persona,
    scenario: Dict[str, object],
    num_agents: int = 4,
    models: List[str] | None = None,
) -> dict[str, object]:
    """Execute a multi-agent test session with visible browser.

    Args:
        persona: The persona for agents to adopt
        scenario: The test scenario to execute
        num_agents: Number of agents in committee (default 3 distinct models)
    """

    # Use scenario's max_turns if specified, otherwise use settings default
    max_turns = scenario.get("max_turns", settings.max_turns)
    
    rprint("\n[bold magenta]🤖 Multi-Agent Vision Testing Framework[/bold magenta]")
    rprint(f"[cyan]Persona:[/cyan] {persona.name}")
    rprint(f"[cyan]Scenario:[/cyan] {scenario.get('name', 'unknown')}")
    rprint(f"[cyan]Committee Size:[/cyan] {num_agents} different models")
    rprint(f"[cyan]Max Turns:[/cyan] {max_turns}")

    # Initialize components
    storage = SessionStorage()
    session_id = storage.start_session(persona=persona, scenario=scenario)
    rprint(f"\n[green]✓ Session ID:[/green] {session_id}")

    # Get screenshots directory from storage (inside test folder)
    screenshots_dir = storage.get_screenshots_dir()
    browser = BrowserAdapter(screenshots_dir=screenshots_dir)
    await browser.start()
    rprint("[green]✓ Browser started (visible mode)[/green]")

    committee = MultiAgentCommittee(persona, num_agents=num_agents, models=models)

    # Navigate to initial page
    initial_url = scenario.get("initial_url", "/")
    # Handle both absolute and relative URLs
    if initial_url.startswith("http"):
        full_url = initial_url
    else:
        full_url = f"{browser.base_url}{initial_url}"
    await browser.page.goto(full_url)
    await browser.page.wait_for_load_state("networkidle")
    rprint(f"[green]✓ Navigated to {initial_url}[/green]")

    # Main testing loop
    scenario_context = scenario.get("initial_state", "You are testing an e-commerce store.")
    test_objective = scenario.get("test_objective", "")
    success_criteria = scenario.get("success_criteria", [])
    success_criteria_text = "\n".join([f"  - {criterion}" for criterion in success_criteria]) if success_criteria else "  - Complete the primary objective"
    success = True
    turns_executed = 0
    
    # Track progress through criteria
    completed_criteria = set()
    action_history = []  # Track recent actions to infer progress
    security_tests_attempted = set()  # Track which security tests have been attempted
    failed_selectors = {}  # Track selectors that have failed multiple times: {selector: count}
    # State guardrails to keep flow on track
    search_add_done = False
    min_filled = False
    max_filled = False
    filtered_add_done = False
    cart_visited = False
    
    # Check if this is a security test scenario
    scenario_name = scenario.get("name", "").lower()
    is_security_test = "security" in scenario_name or "security" in scenario.get("description", "").lower()

    for turn_idx in range(1, max_turns + 1):
        turns_executed = turn_idx
        rprint(f"\n[bold yellow]{'='*60}[/bold yellow]")
        rprint(f"[bold yellow]Turn {turn_idx}/{max_turns}[/bold yellow]")
        rprint(f"[bold yellow]{'='*60}[/bold yellow]")

        # Capture screenshot BEFORE agent decision
        screenshot_path = await browser.capture_screenshot(session_id, turn_idx)
        rprint(f"[dim]📸 Screenshot saved: {screenshot_path}[/dim]")

        # Get current page state and prepend scenario context
        browser_state = await browser.get_current_state()
        current_url = browser.page.url.replace(browser.base_url, "")
        if "/cart" in current_url:
            cart_visited = True
        
        # Update progress tracking based on current state and action history
        # Check if we've navigated to products page
        if "/products" in current_url and "Navigate to products page" not in completed_criteria:
            completed_criteria.add("Navigate to products page and view product listings")
        
        # Check if we've added to cart (based on action history)
        recent_add_to_cart = any(
            "add-to-cart" in str(action.get("target", "")).lower() 
            for action in action_history[-3:]  # Check last 3 actions
        )
        if recent_add_to_cart and "Add at least one product to cart" not in completed_criteria:
            completed_criteria.add("Add at least one product to cart")
        
        # Check if we've viewed cart
        if "/cart" in current_url and "View cart to verify" not in completed_criteria:
            completed_criteria.add("View cart to verify the item was successfully added")
        
        # Build progress section
        remaining_criteria = [c for c in success_criteria if c not in completed_criteria]
        progress_text = ""
        if completed_criteria:
            progress_text = "\n=== PROGRESS ===\n"
            progress_text += "Completed:\n"
            for criterion in completed_criteria:
                progress_text += f"  ✓ {criterion}\n"
        if remaining_criteria:
            progress_text += "\nRemaining:\n"
            for criterion in remaining_criteria:
                progress_text += f"  - {criterion}\n"
        else:
            progress_text += "\n✓ ALL CRITERIA COMPLETED! Use 'report' action to signal completion.\n"
        
        # Format action history with failure hints
        history_text = ""
        if action_history:
            history_text = "\n=== ACTION HISTORY (Last 5 actions) ===\n"
            for i, action in enumerate(action_history):
                payload_info = ""
                if action.get("payload") and isinstance(action["payload"], dict):
                    value = action["payload"].get("value", "")
                    if value:
                        # Truncate long payloads for display
                        display_value = value[:50] + "..." if len(value) > 50 else value
                        payload_info = f" (value: {display_value})"

                success_indicator = "✓" if action.get("success", True) else "✗"
                history_text += f"{i+1}. {success_indicator} {action['type']} -> {action['target']}{payload_info}\n"

            # Add hints if last action failed
            if action_history and not action_history[-1].get("success", True):
                last_action = action_history[-1]
                history_text += "\n⚠️  LAST ACTION FAILED! Consider:\n"
                if last_action["type"] == "click":
                    history_text += "  - Try a simpler selector (e.g., '.add-to-cart' instead of complex nth-child)\n"
                    history_text += "  - Use [data-testid] attributes if available\n"
                    history_text += "  - Try scrolling first if element is off-screen\n"
                    history_text += "  - Try a different action if selector is incorrect\n"

                # Show failed selectors to avoid
                if failed_selectors:
                    history_text += "\n❌ FAILED SELECTORS (DO NOT USE THESE):\n"
                    for selector, count in failed_selectors.items():
                        history_text += f"  - {selector} (failed {count}x)\n"
        else:
            history_text = "\n=== ACTION HISTORY ===\nNo actions taken yet.\n"
        
        # Add security test tracking for security scenarios
        security_test_info = ""
        scenario_name = scenario.get("name", "").lower()
        is_security_test = "security" in scenario_name or "security" in scenario.get("description", "").lower()
        if is_security_test and security_tests_attempted:
            security_test_info = "\n=== SECURITY TESTS ATTEMPTED ===\n"
            for test in sorted(security_tests_attempted):
                security_test_info += f"  ✓ {test}\n"
            security_test_info += "\nContinue testing different security vulnerabilities. Don't repeat the same test with the same payload.\n"

        observation = f"""=== TEST CONTEXT ===
{scenario_context}

=== PRIMARY OBJECTIVE ===
{test_objective}

=== SUCCESS CRITERIA (You must complete ALL of these) ===
{success_criteria_text}
{progress_text}
{history_text}
{security_test_info}
IMPORTANT: Use the "report" action with type="report" and target="task_complete" ONLY when ALL success criteria have been met. Until then, continue taking actions to complete the task.

=== CURRENT PAGE STATE ===
{browser_state}"""
        # Print full observation for debugging (or truncate if too long)
        observation_preview = observation[:800] + "..." if len(observation) > 800 else observation
        rprint(f"\n[blue]Observation:[/blue]\n{observation_preview}")

        # Committee decision
        try:
            consensus_action, all_proposals, confidence_scores = committee.decide(
                observation, screenshot_path
            )

            # Hard guardrail: once search add is done, force move to products (no more adds on search)
            if (
                search_add_done
                and "/search" in current_url
                and "add-to-cart" in str(consensus_action.target)
            ):
                consensus_action = Action(type="navigate", target="/products", payload=None)

            # Hard guardrail: after filters filled, prioritize adding filtered item, not new searches
            if min_filled and max_filled and not filtered_add_done:
                if consensus_action.type == "fill" and str(consensus_action.target).startswith("#searchInput"):
                    consensus_action = Action(type="click", target=".add-to-cart", payload={"selector": ".add-to-cart"})
                if consensus_action.type == "click" and "search-button" in str(consensus_action.target):
                    consensus_action = Action(type="click", target=".add-to-cart", payload={"selector": ".add-to-cart"})
            # If trying to add-to-cart before both filters are set, force completing filters first
            if search_add_done and not (min_filled and max_filled) and consensus_action.type == "click" and "add-to-cart" in str(consensus_action.target):
                if not min_filled:
                    consensus_action = Action(type="fill", target="#minPrice", payload={"selector": "#minPrice", "value": "10"})
                elif not max_filled:
                    consensus_action = Action(type="fill", target="#maxPrice", payload={"selector": "#maxPrice", "value": "200"})

            # Hard guardrail: after filtered add, go to cart
            if filtered_add_done and not cart_visited:
                if not (consensus_action.type == "click" and ("go-to-cart" in str(consensus_action.target) or "/cart" in str(consensus_action.target))):
                    consensus_action = Action(type="click", target=".go-to-cart", payload={"selector": ".go-to-cart"})
            
            # LOOP DETECTION: Check if we are repeating the exact same action as the last one
            # Allow same action if payload is different (e.g., testing different security payloads)
            # Also allow retry if the last action failed (e.g., timeout, wrong selector)
            if action_history:
                last_action = action_history[-1]
                is_same_action = (consensus_action.type == last_action["type"] and
                                 consensus_action.target == last_action["target"])

                # If last action failed, allow retry with same or different approach
                if is_same_action and not last_action.get("success", True):
                    rprint(f"[yellow]⚠ Retrying action after previous failure - allowing[/yellow]")
                elif is_same_action:
                    # Check if payload is different (for fill actions, different values are allowed)
                    if consensus_action.type == "fill" and consensus_action.payload:
                        last_payload_value = last_action.get("payload", {}).get("value", "") if isinstance(last_action.get("payload"), dict) else ""
                        current_payload_value = consensus_action.payload.get("value", "") if consensus_action.payload else ""
                        
                        # If payload values are different, allow it (testing different security payloads)
                        if last_payload_value != current_payload_value:
                            rprint(f"[yellow]⚠ Same action with different payload - allowing (testing different security payload)[/yellow]")
                        else:
                            # Same action, same payload - check if we've done other actions in between
                            # Allow if we've done at least 2 different actions since last time
                            recent_actions = action_history[-3:] if len(action_history) >= 3 else action_history
                            unique_actions = set((a["type"], a["target"]) for a in recent_actions)
                            
                            if len(unique_actions) <= 1:
                                # We're stuck in a loop with no variation
                                error_msg = f"Loop detected: Agents attempted to repeat action '{consensus_action.type} -> {consensus_action.target}' with same payload immediately."
                                rprint(f"\n[bold red]🛑 {error_msg}[/bold red]")
                                rprint("[red]Aborting session to prevent infinite loop.[/red]")
                                
                                storage.log_turn(
                                    turn=turn_idx,
                                    action_type=consensus_action.type,
                                    action_target=consensus_action.target,
                                    screenshot_path=screenshot_path,
                                    agent_proposals=all_proposals,
                                    consensus_action=consensus_action.model_dump(),
                                    confidence_scores=confidence_scores,
                                    success=False,
                                    latency=0.0,
                                    safety_pass=True,
                                    validators=[f"loop_detected:{error_msg}"],
                                    conclusion="",
                                    page_state=observation,
                                    issues_found=error_msg,
                                    issues_description=error_msg,
                                )
                                success = False
                                break
                            else:
                                rprint(f"[yellow]⚠ Same action repeated, but other actions were taken - allowing[/yellow]")
                    else:
                        # For non-fill actions, check if it's actually a problematic loop
                        # Allow if: 1) page state changed, 2) action succeeded and could reasonably be done again
                        # For click actions specifically, check if this is a reasonable repetition
                        should_block_loop = True
                        if consensus_action.type == "click" and last_action.get("success", False):
                            # If last click succeeded, this might be intentional (e.g., adding multiple items)
                            # Only block if we've done the same click multiple times in a row
                            recent_same_clicks = sum(
                                1 for a in action_history[-3:]
                                if a["type"] == "click" and a["target"] == consensus_action.target
                            )
                            if recent_same_clicks >= 2:
                                # Clicking same thing 3+ times in a row is definitely a loop
                                error_msg = f"Loop detected: Agents clicked '{consensus_action.target}' {recent_same_clicks + 1} times in a row."
                                rprint(f"\n[bold red]🛑 {error_msg}[/bold red]")
                                rprint("[red]Aborting session to prevent infinite loop.[/red]")
                            else:
                                # Allow one repetition (might be adding another item, etc.)
                                rprint(f"[yellow]⚠ Same click action repeated - allowing (might be adding multiple items)[/yellow]")
                                should_block_loop = False
                        else:
                            # For other non-fill actions, same action+target is a loop
                            error_msg = f"Loop detected: Agents attempted to repeat action '{consensus_action.type} -> {consensus_action.target}' immediately."
                            rprint(f"\n[bold red]🛑 {error_msg}[/bold red]")
                            rprint("[red]Aborting session to prevent infinite loop.[/red]")

                        if should_block_loop:
                            storage.log_turn(
                                turn=turn_idx,
                                action_type=consensus_action.type,
                                action_target=consensus_action.target,
                                screenshot_path=screenshot_path,
                                agent_proposals=all_proposals,
                                consensus_action=consensus_action.model_dump(),
                                confidence_scores=confidence_scores,
                                success=False,
                                latency=0.0,
                                safety_pass=True,
                                validators=[f"loop_detected:{error_msg}"],
                                conclusion="",
                                page_state=observation,
                                issues_found=error_msg,
                                issues_description=error_msg,
                            )
                            success = False
                            break
                    
        except Exception as e:
            rprint(f"\n[red]❌ Committee decision failed: {e}[/red]")
            success = False
            break

        # Validate action
        # Disable safety checks for security testing scenarios
        passed, reasons, safety_reasons = validate_action(consensus_action, persona, disable_safety_checks=is_security_test)
        safety_pass = len(safety_reasons) == 0

        if not passed:
            rprint(f"\n[red]❌ Validation failed:[/red]")
            for reason in reasons:
                rprint(f"  - {reason}")

            storage.log_turn(
                turn=turn_idx,
                action_type=consensus_action.type,
                action_target=consensus_action.target,
                screenshot_path=screenshot_path,
                agent_proposals=all_proposals,
                consensus_action=consensus_action.model_dump(),
                confidence_scores=confidence_scores,
                success=False,
                latency=0.0,
                safety_pass=safety_pass,
                validators=reasons,
                conclusion="",
                page_state=observation,
                issues_found="; ".join(reasons),
                issues_description="; ".join(reasons),
            )
            success = False
            break

        rprint("[green]✓ Validation passed[/green]")

        # Execute action
        try:
            new_observation, latency = await browser.execute(consensus_action)
            rprint(f"\n[magenta]Response:[/magenta] {new_observation[:300]}...")
            rprint(f"[dim]⏱️  Latency: {latency:.3f}s[/dim]")

            # Extract conclusion if this is a report action
            conclusion = ""
            if consensus_action.type == "report":
                conclusion = consensus_action.target

            storage.log_turn(
                turn=turn_idx,
                action_type=consensus_action.type,
                action_target=consensus_action.target,
                screenshot_path=screenshot_path,
                agent_proposals=all_proposals,
                consensus_action=consensus_action.model_dump(),
                confidence_scores=confidence_scores,
                success=True,
                latency=latency,
                safety_pass=safety_pass,
                validators=["ok"],
                conclusion=conclusion,
                page_state=new_observation,
                issues_found="",
                issues_description="",
            )

            # Track action in history for progress inference
            action_payload = consensus_action.payload if consensus_action.payload else {}
            # Check if action succeeded or failed based on response
            action_succeeded = not any(err in new_observation for err in ["ERROR", "CLICK_ERROR", "FILL_ERROR", "NAVIGATE_ERROR"])

            # Update guardrail flags based on successful actions
            if action_succeeded:
                if consensus_action.type == "click" and "add-to-cart" in str(consensus_action.target):
                    if "/search" in current_url:
                        search_add_done = True
                    if min_filled and max_filled:
                        filtered_add_done = True
                if consensus_action.type == "fill" and str(consensus_action.target) == "#minPrice":
                    min_filled = True
                if consensus_action.type == "fill" and str(consensus_action.target) == "#maxPrice":
                    max_filled = True
                if "/cart" in browser.page.url.replace(browser.base_url, ""):
                    cart_visited = True

            # Track failed selectors for click actions
            if not action_succeeded and consensus_action.type == "click":
                selector = consensus_action.target
                failed_selectors[selector] = failed_selectors.get(selector, 0) + 1

            action_history.append({
                "type": consensus_action.type,
                "target": consensus_action.target,
                "payload": action_payload,
                "turn": turn_idx,
                "success": action_succeeded
            })
            
            # Track security tests attempted
            if is_security_test:
                if consensus_action.type == "fill" and action_payload:
                    value = action_payload.get("value", "")
                    target = consensus_action.target
                    # Identify test type from payload
                    if "<script" in value.lower() or "alert" in value.lower():
                        security_tests_attempted.add(f"XSS test in {target}")
                    elif "' OR" in value.upper() or "1=1" in value:
                        security_tests_attempted.add(f"SQL injection test in {target}")
                    elif value.startswith("-") and target in ["#minPrice", "#maxPrice"]:
                        security_tests_attempted.add(f"Negative value test in {target}")
                    elif not value.replace("-", "").replace(".", "").isdigit() and target in ["#minPrice", "#maxPrice"]:
                        security_tests_attempted.add(f"Non-numeric test in {target}")
                    else:
                        security_tests_attempted.add(f"Input validation test in {target}")
            # Keep only last 5 actions
            if len(action_history) > 5:
                action_history.pop(0)

            observation = new_observation

            # Check if task is complete
            if consensus_action.type == "report":
                rprint("\n[bold green]✓ Task reported as complete by agents[/bold green]")
                break
            
            # Early stopping: If all criteria are completed, encourage reporting
            current_remaining = [c for c in success_criteria if c not in completed_criteria]
            if len(current_remaining) == 0 and consensus_action.type != "report":
                rprint("\n[yellow]⚠ All success criteria appear to be completed. Consider using 'report' action.[/yellow]")

        except Exception as e:
            rprint(f"\n[red]❌ Execution failed: {e}[/red]")
            storage.log_turn(
                turn=turn_idx,
                action_type=consensus_action.type,
                action_target=consensus_action.target,
                screenshot_path=screenshot_path,
                agent_proposals=all_proposals,
                consensus_action=consensus_action.model_dump(),
                confidence_scores=confidence_scores,
                success=False,
                latency=0.0,
                safety_pass=safety_pass,
                validators=[f"execution_error:{str(e)}"],
                conclusion="",
            )
            success = False
            break

    # Cleanup
    await browser.stop()
    csv_path = storage.end_session()

    # Final summary
    status = "completed" if success else "failed"
    rprint(f"\n[bold]{'='*60}[/bold]")
    rprint(f"[bold cyan]Session Summary[/bold cyan]")
    rprint(f"[bold]{'='*60}[/bold]")
    rprint(f"[cyan]Status:[/cyan] {status}")
    rprint(f"[cyan]Turns Executed:[/cyan] {turns_executed}")
    rprint(f"[cyan]CSV Report:[/cyan] {csv_path}")
    rprint(f"[bold]{'='*60}[/bold]\n")

    return {
        "session_id": session_id,
        "status": status,
        "success": success,
        "turns_executed": turns_executed,
        "csv_path": csv_path,
        "persona": persona.model_dump(),
        "scenario": scenario,
    }
